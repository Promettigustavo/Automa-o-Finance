# emissao_deposito.py
from __future__ import annotations
import datetime as dt
from pathlib import Path
import re, unicodedata
from decimal import Decimal, ROUND_DOWN, InvalidOperation
import pandas as pd

from meu_numero_state import MeuNumeroState  # <<< contador diário compartilhado

# ========= Config/compat =========
# Usado como fallback se a função não receber o parâmetro explicitamente
PAPEL_PARTICIPANTE = "02"  # "02" = emissor (default), "03" = distribuidor

# -------------------- helpers --------------------
def _fmt_x(value: str, length: int) -> str:
    s = unicodedata.normalize("NFKD", (value or ""))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[\r\n\t]", " ", s)
    return (s[:length]).ljust(length, " ")

def _fmt_9(value: int | str, length: int) -> str:
    s = "".join(ch for ch in str(value) if ch.isdigit())
    if len(s) > length:
        s = s[-length:]
    return s.zfill(length)

def _fmt_decimal(val, int_len: int, dec_len: int) -> str:
    """
    Converte val para Decimal com locale-agnostic:
    - Aceita 1234,56 ; 1.234,56 ; 1234.56 ; 1234 ; floats ; Decimals.
    - Quantiza com ROUND_DOWN para 'dec_len' casas.
    - Retorna sem separador decimal, padding à esquerda.
    """
    # 1) Normaliza para Decimal
    if val is None or (isinstance(val, float) and pd.isna(val)):
        d = Decimal(0)
    else:
        try:
            if isinstance(val, Decimal):
                d = val
            elif isinstance(val, (int, float)):
                d = Decimal(str(val))
            else:
                s = str(val).strip()
                s = re.sub(r"[^\d,.\-]", "", s)

                if "," in s and "." in s:
                    s = s.replace(".", "").replace(",", ".")
                elif "," in s:
                    s = s.replace(",", ".")
                d = Decimal(s)
        except Exception:
            d = Decimal(0)

    # 2) Quantiza e formata
    q = Decimal(1).scaleb(-dec_len)  # 10^-dec_len
    d = d.quantize(q, rounding=ROUND_DOWN)
    s = f"{d:.{dec_len}f}".replace(".", "")

    # 3) Garante somente dígitos e comprimento certo
    s = re.sub(r"[^0-9]", "", s)
    need = int_len + dec_len
    if len(s) > need:
        s = s[-need:]
    return s.zfill(need)


def _date_yyyymmdd(d: dt.date | str | None) -> str:
    if d is None:
        d = dt.date.today()
    if isinstance(d, str):
        s = d.strip()
        if len(s) == 8 and s.isdigit():
            return s
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
            try:
                return dt.datetime.strptime(s, fmt).strftime("%Y%m%d")
            except Exception:
                pass
        dd = pd.to_datetime(d, dayfirst=True, errors="coerce")
        if pd.isna(dd):
            raise ValueError(f"Data inválida: {d!r}")
        return dd.strftime("%Y%m%d")
    return d.strftime("%Y%m%d")

def _norm_col(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.strip())
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^A-Za-z0-9_ /-]", "", s)
    s = re.sub(r"\s+", " ", s.replace("-", " ").replace("/", " "))
    return s.upper().replace(" ", "_")

def _coalesce(df: pd.DataFrame, candidates: list[str]) -> str | None:
    want = {_norm_col(c) for c in candidates}
    for c in df.columns:
        if _norm_col(c) in want:
            return c
    for c in df.columns:
        if any(w in _norm_col(c) for w in want):
            return c
    return None

def _sanitize_papel(papel: str | int | None) -> str:
    """
    Normaliza o papel do participante.
    Aceita: "02"/2 -> "02" (emissor); "03"/3 -> "03" (distribuidor).
    """
    if papel is None:
        papel = PAPEL_PARTICIPANTE
    s = str(papel).strip()
    if s in {"2", "02"}:
        return "02"
    if s in {"3", "03"}:
        return "03"
    raise ValueError("papel_participante inválido (use '02' para emissor ou '03' para distribuidor).")

# -------------------- builders --------------------
def build_header(data_operacao: dt.date | str | None = None) -> str:
    partes = [
        _fmt_x("MDA", 5),                         # 01-05
        _fmt_9(0, 1),                              # 06
        _fmt_x("0401", 4),                         # 07-10
        _fmt_9(_date_yyyymmdd(data_operacao), 8),  # 11-18
    ]
    linha = "".join(partes)
    assert len(linha) == 18
    return linha

def build_registro(
    meu_numero: int | str,
    codigo_cetip_ativo: str,
    conta_cetip_contraparte: str,   # 34-41  9(08)
    conta_cetip_emissor: str,       # 42-49  9(08)
    qtde_de_cotas,                  # 50-69  9(12)^9(8)
    p_u,                            # 70-87  9(10)^9(8)
    papel_participante: str = "02", # 90-91 9(02) -> 02 (emissor) / 03 (distribuidor)
) -> str:
    """
    Registro (agora 91 col):
    01-05 'MDA' | 06 '1' | 07-10 '0401' | 11-20 meu número | 21-22 '00'
    23-33 Código_Cetip_Ativo (X11)
    34-41 Conta_Cetip_contraparte (9(08))
    42-49 Conta_Cetip_Emissor     (9(08))
    50-69 Quantidade depositada   (9(12)^9(8))
    70-87 PU (Preço Unitário)     (9(10)^9(8))
    88-89 Modalidade liquidação   (9(02)) -> '00' fixo
    90-91 Papel do participante   (9(02)) -> '02' emissor | '03' distribuidor
    """
    papel = _sanitize_papel(papel_participante)

    partes = [
        _fmt_x("MDA", 5),                           # 01-05
        _fmt_9(1, 1),                               # 06
        _fmt_9(401, 4),                             # 07-10 -> 0401
        _fmt_9(meu_numero, 10),                     # 11-20
        _fmt_9(0, 2),                               # 21-22 -> 00
        _fmt_x(str(codigo_cetip_ativo), 11),        # 23-33
        _fmt_9(conta_cetip_contraparte, 8),         # 34-41
        _fmt_9(conta_cetip_emissor, 8),             # 42-49
        _fmt_decimal(qtde_de_cotas, 12, 8),         # 50-69
        _fmt_decimal(p_u,           10, 8),         # 70-87
        _fmt_9(0, 2),                               # 88-89 -> 00 (modalidade liquidação)
        _fmt_9(papel, 2),                           # 90-91 -> papel do participante
    ]
    linha = "".join(partes)
    assert len(linha) == 91, f"Tamanho do registro inesperado: {len(linha)}"
    return linha

# -------------------- API p/ launcher --------------------
def gerar_emissao_deposito_from_excel(
    caminho_planilha: str | Path,
    arquivo_saida: str | Path = "Emissao_Deposito.txt",
    sheet_index: int = 1,
    data_operacao: dt.date | str | None = None,
    quebra_linha: str = "\n",
    papel_participante: str | int | None = None,
) -> Path:
    """
    Gera 1 Header + 1 registro por linha válida da planilha.

    Colunas esperadas (nomes flexíveis):
      - Codigo_Cetip_Ativo
      - Conta_Cetip_contraparte
      - Conta_Cetip_Emissor
      - Qtde_de_Cotas
      - P_U

    Parâmetros:
      - papel_participante: '02' (emissor) ou '03' (distribuidor).
        Se None, usa a variável global PAPEL_PARTICIPANTE.
    """
    caminho_planilha = Path(caminho_planilha)

    # Tenta a aba indicada; se não existir, cai pra 0
    try:
        df = pd.read_excel(caminho_planilha, sheet_name=sheet_index)
    except Exception:
        df = pd.read_excel(caminho_planilha, sheet_name=0)

    col_codigo = _coalesce(df, ["Codigo_Cetip_Ativo", "Código Cetip Ativo", "CODIGO_CETIP_ATIVO", "CODIGO_CETIP"])
    if not col_codigo:
        raise KeyError("Coluna 'Codigo_Cetip_Ativo' não encontrada na planilha.")

    col_ctp = _coalesce(df, ["Conta_Cetip_contraparte", "CONTA CETIP CONTRAPARTE", "CONTA_CETIP_CONTRAPARTE"])
    if not col_ctp:
        raise KeyError("Coluna 'Conta_Cetip_contraparte' não encontrada na planilha.")

    col_emissor = _coalesce(df, ["Conta_Cetip_Emissor", "CONTA CETIP EMISSOR", "CONTA_CETIP_EMISSOR"])
    if not col_emissor:
        raise KeyError("Coluna 'Conta_Cetip_Emissor' não encontrada na planilha.")

    col_qtd = _coalesce(df, ["Qtde_de_Cotas", "QTD", "QUANTIDADE", "QTDE_DE_COTAS"])
    if not col_qtd:
        raise KeyError("Coluna 'Qtde_de_Cotas' não encontrada na planilha.")

    col_pu = _coalesce(df, ["P_U", "PU", "PRECO_UNITARIO", "PREÇO_UNITARIO", "PRECO UNITARIO"])
    if not col_pu:
        raise KeyError("Coluna 'P_U' não encontrada na planilha.")

    papel = _sanitize_papel(papel_participante)

    # coleta linhas válidas
    linhas_validas = []
    for _, row in df.iterrows():
        cod = str(row[col_codigo]).strip()
        if not cod or cod.lower() == "nan":
            continue
        ctp = "" if pd.isna(row[col_ctp]) else str(row[col_ctp]).strip()
        emi = "" if pd.isna(row[col_emissor]) else str(row[col_emissor]).strip()
        qtd = 0 if pd.isna(row[col_qtd]) else row[col_qtd]
        pu  = 0 if pd.isna(row[col_pu])  else row[col_pu]
        linhas_validas.append((cod, ctp, emi, qtd, pu))

    # === ALOCAÇÃO GLOBAL DE 'MEU_NUMERO' (único por dia para todo o sistema) ===
    dia = _date_yyyymmdd(data_operacao)
    state_dir = Path(arquivo_saida).parent  # salva estado ao lado do arquivo de saída
    mn_state = MeuNumeroState(state_dir)
    meus_formatados = mn_state.allocate_batch(dia, len(linhas_validas))  # ['0000000001', '0000000002', ...]

    linhas = [build_header(data_operacao)]
    for i, (cod, ctp, emi, qtd, pu) in enumerate(linhas_validas):
        linhas.append(
            build_registro(
                meu_numero=meus_formatados[i],
                codigo_cetip_ativo=cod,
                conta_cetip_contraparte=ctp,
                conta_cetip_emissor=emi,
                qtde_de_cotas=qtd,
                p_u=pu,
                papel_participante=papel,
            )
        )

    out = Path(arquivo_saida)
    out.write_text(quebra_linha.join(linhas), encoding="utf-8")
    return out

if __name__ == "__main__":
    pass
