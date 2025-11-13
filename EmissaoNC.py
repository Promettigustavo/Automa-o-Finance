# cnab_553_header_e_nc_final.py
from __future__ import annotations
import datetime as dt
from pathlib import Path
import unicodedata
import re
import pandas as pd
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from tkinter import Tk, filedialog  # <- sem messagebox

# =========================
# Constantes de Header/NC
# =========================
HEADER_PREFIX = "NC   0INCLLIMINETRUSTDTVM     "
HEADER_SUFFIX = "00004<"
HEADER_LEN = 44

NC_PREFIX = "NC   1INCL              0000"
NC_LEN = 553

TIPO_EMISSAO_FIXO = "N"    # pos 29 (índice 28)
FORMATO_EMISSAO_FIXO = "E" # pos 38 (índice 37)
TIPO_REGIME_FIXO = "2"     # pos 185 (índice 184)
CARACTERE_186_FIXO = "S"   # pos 186 (índice 185)

# Ler sempre a 2ª aba por padrão
SHEET_INDEX = 1  # 0 = primeira, 1 = segunda

# =========================
# Utils de texto/colunas
# =========================
def normalize_colname(s: str) -> str:
    s = s.strip()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^A-Za-z0-9_ ]+", " ", s)
    s = re.sub(r"\s+", "_", s.upper().strip())
    return s

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [normalize_colname(c) for c in df.columns]
    return df

def strip_accents(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(ch for ch in s if not unicodedata.combining(ch))

def clean_text_field(s: str) -> str:
    s = strip_accents(s or "").upper()
    s = re.sub(r"[^A-Z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

# =========================
# Seleção e leitura da planilha
# =========================
def choose_file() -> Path:
    Tk().withdraw()
    path = filedialog.askopenfilename(
        title="Selecione a planilha de entrada",
        filetypes=[
            ("Planilhas Excel", "*.xlsx;*.xlsm;*.xltx;*.xltm"),
            ("CSV", "*.csv"),
            ("Todos", "*.*"),
        ],
    )
    if not path:
        # Sem pop-up: encerra silenciosamente
        raise SystemExit("Nenhum arquivo selecionado.")
    return Path(path)

def read_any_table(path: Path, sheet_index: int | None = None) -> pd.DataFrame:
    suffix = path.suffix.lower()
    idx = SHEET_INDEX if sheet_index is None else sheet_index
    if suffix in {".xlsx", ".xlsm", ".xltx", ".xltm"}:
        df = pd.read_excel(path, dtype=object, engine="openpyxl", sheet_name=idx)
    elif suffix == ".csv":
        df = pd.read_csv(path, dtype=object, sep=",", encoding="utf-8", keep_default_na=True)
    else:
        raise ValueError(f"Formato não suportado: {suffix} (aceitos: .xlsx, .xlsm, .xltx, .xltm, .csv)")

    def _clean_cell(x):
        if pd.isna(x):
            return ""
        if isinstance(x, (pd.Timestamp, dt.date, dt.datetime)):
            return x
        s = str(x).strip()
        return "" if s.lower() in {"nan", "none", "null", "<na>", "nat"} else s

    try:
        return df.map(_clean_cell)
    except AttributeError:
        return df.applymap(_clean_cell)

# =========================
# Datas e validações
# =========================
def build_header(date: dt.date | None = None) -> str:
    d = date or dt.date.today()
    header = f"{HEADER_PREFIX}{d.strftime('%Y%m%d')}{HEADER_SUFFIX}"
    if len(header) != HEADER_LEN:
        raise ValueError(f"Header inválido: {len(header)} (esperado {HEADER_LEN})")
    return header

def normalize_date_any(value, field_name: str) -> str:
    if isinstance(value, (dt.datetime, dt.date, pd.Timestamp)):
        if isinstance(value, dt.datetime):
            value = value.date()
        return value.strftime("%Y%m%d")

    s = (str(value or "").strip())
    if not s:
        raise ValueError(f"{field_name} ausente")

    if re.search(r"[^\d]", s):
        ts = pd.to_datetime(s, errors="coerce", dayfirst=True)
        if pd.isna(ts):
            ts = pd.to_datetime(s, errors="coerce", dayfirst=False)
        if not pd.isna(ts):
            return ts.strftime("%Y%m%d")

    digits = re.sub(r"\D", "", s)

    if len(digits) == 8:
        y1, m1, d1 = int(digits[:4]), int(digits[4:6]), int(digits[6:8])
        try:
            dt.date(y1, m1, d1)
            return f"{y1:04d}{m1:02d}{d1:02d}"
        except ValueError:
            pass
        d2, m2, y2 = int(digits[:2]), int(digits[2:4]), int(digits[4:8])
        try:
            dt.date(y2, m2, d2)
            return f"{y2:04d}{m2:02d}{d2:02d}"
        except ValueError:
            pass

    if len(digits) == 7:
        d, m, y = int(digits[0]), int(digits[1:3]), int(digits[3:7])
        try:
            dt.date(y, m, d)
            return f"{y:04d}{m:02d}{d:02d}"
        except ValueError:
            pass

    raise ValueError(f"Data inválida (informe AAAAMMDD, ex.: 20250903): '{s}'")

def days_diff_yyyymmdd(start_yyyymmdd: str, end_yyyymmdd: str) -> int:
    d1 = dt.datetime.strptime(start_yyyymmdd, "%Y%m%d").date()
    d2 = dt.datetime.strptime(end_yyyymmdd, "%Y%m%d").date()
    if d2 < d1:
        raise ValueError("DATA_DE_VENCIMENTO anterior à DATA_DE_EMISSAO")
    return (d2 - d1).days

# =========================
# Mapas
# =========================
def map_especie_garantia(v: str) -> str:
    s = (v or "").strip().upper()
    if "FLUTUANTE" in s:
        return "1"
    if "QUIROGRAF" in s:
        return "2"
    if "REAL" in s:
        return "3"
    if "SUBORDINADA" in s:
        return "5"
    if s in {"", "SEM", "SEM GARANTIA"}:
        return "4"
    return "4"

def _strip_accents_upper(s: str) -> str:
    s = (s or "").strip().upper()
    s = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch))

def map_indexador(v: str) -> str:
    s = _strip_accents_upper(v)
    if s == "VCP":
        return "0000"
    if s == "SELIC":
        return "0001"
    if s == "DI":
        return "0003"
    if s == "TR":
        return "0020"
    if s in {"PRE", "PRE-FIXADO", "PRE FIXADO", "PREFIXADO"}:
        return "0099"
    raise ValueError("INDEXADOR inválido/ausente (use VCP, SELIC, DI, TR ou PRE-FIXADO)")

def map_criterio_calc_juros(v: str) -> str:
    s = (v or "").strip().upper()
    mapping = {
        "252-NÚMERO DIAS ÚTEIS ENTRE A DATA DE INÍCIO OU O ÚLTIMO PAGAMENTO E O PRÓXIMO": "01",
        "252-NÚMERO DE MESES ENTRE A DATA DE INÍCIO OU ÚLTIMO PAGAMENTO E O PRÓXIMO X 21": "02",
        "360-NÚMERO DIAS CORRIDOS ENTRE A DATA DE INÍCIO OU ÚLTIMO PAGAMENTO E O PRÓXIMO": "03",
        "360-NÚMERO DE MESES ENTRE A DATA DE INÍCIO OU O PRÓXIMO X 30": "04",
        "365-NÚMERO DIAS CORRIDOS ENTRE A DATA DE INÍCIO OU ÚLTIMO PAGAMENTO E O PRÓXIMO": "05",
        "365-NÚMERO DE MESES ENTRE A DATA DE INÍCIO OU O PRÓXIMO X 30": "06",
    }
    return mapping.get(s, "")

# =========================
# Montagem do registro NC
# =========================
def build_nc(
    data_emissao: str,
    data_vencimento: str,
    qtd_emitida: str,
    valor_unitario: str,
    avalista_val: str | None,
    especie_garantia_val: str | None,
    indexador_val: str | None,
    tipo_indicador_vcp_val: str | None,
    taxa_flu_val: str | None,
    criterio_val: str | None,
    taxa_spread_val: str | None,
    nome_emissor_val: str | None,
    cnpj_emissor_val: str | None,
) -> str:
    de = normalize_date_any(data_emissao, "DATA_DE_EMISSAO")
    dv = normalize_date_any(data_vencimento, "DATA_DE_VENCIMENTO")
    diff_str = str(days_diff_yyyymmdd(de, dv)).rjust(10, "0")

    qtd_str = re.sub(r"\D+", "", str(qtd_emitida or "").strip())
    if qtd_str == "":
        raise ValueError("QUANTIDADE_EMITIDA ausente ou inválida")
    qtd_str = str(int(qtd_str)).rjust(10, "0")

    try:
        dec = Decimal(str(valor_unitario).replace(",", "."))
    except InvalidOperation:
        raise ValueError(f"VALOR_UNITARIO inválido: '{valor_unitario}'")
    dec = dec.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
    valor_str = str(int(dec * (10**8))).rjust(24, "0")

    valor_fin = (Decimal(qtd_str) * dec).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    valor_fin_str = str(int(valor_fin * 100)).rjust(12, "0")

    avalista = clean_text_field(re.sub(r"\s+", " ", (avalista_val or "").strip()) or "NAO HA")
    avalista_field = avalista[:50].ljust(50)

    especie = map_especie_garantia(especie_garantia_val or "")
    indexador = map_indexador(indexador_val or "")

    vcp_tipo_field = " " * 10
    if indexador == "0000":
        nums = re.sub(r"\D", "", (tipo_indicador_vcp_val or "").strip())
        if nums == "":
            raise ValueError("TIPO_INDICADOR_VCP obrigatório quando INDEXADOR=VCP")
        vcp_tipo_field = nums.rjust(10, "0")

    taxa_field = " " * 5
    if indexador in {"0001", "0003", "0000"}:
        raw = (taxa_flu_val or "").replace(",", ".").strip()
        if raw:
            tdec = Decimal(raw).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
            taxa_field = str(int(tdec * 100)).rjust(5, "0")
        elif indexador in {"0001", "0003"}:
            raise ValueError("TAXA_FLUTUANTE obrigatória para INDEXADOR=SELIC/DI")

    crit_field = " "
    if taxa_field.strip():
        code = map_criterio_calc_juros(criterio_val or "")
        if code not in {"01", "02", "03", "04", "05", "06"}:
            raise ValueError("CRITERIO_CALCULO_JUROS inválido/ausente")
        crit_field = code

    buf = list(NC_PREFIX.ljust(NC_LEN, " "))
    buf[28] = TIPO_EMISSAO_FIXO
    buf[29:37] = list("33738404")
    buf[37] = FORMATO_EMISSAO_FIXO
    buf[38:46] = list("33738002")
    buf[46:58] = list(" " * 12)
    buf[58] = "1"
    buf[59:62] = list(" ")
    buf[62:72] = list("UNICA".ljust(10))
    buf[72:80] = list(de)
    buf[80:88] = list(dv)
    buf[88:98] = list(diff_str)
    today_str = dt.date.today().strftime("%Y%m%d")
    buf[98:106] = list(today_str)
    buf[106:116] = list(qtd_str)
    buf[116:140] = list(valor_str)
    buf[140:152] = list(valor_fin_str)
    buf[152:184] = list(" " * 32)
    buf[184] = TIPO_REGIME_FIXO
    buf[185] = CARACTERE_186_FIXO
    buf[186:216] = list("PRIVADA".ljust(30))
    buf[216:221] = list("2080".ljust(5))
    buf[221:229] = list("20231113")
    buf[229] = "S"
    buf[230] = " "
    buf[231:281] = list(avalista_field)
    buf[281] = "N"
    buf[282:300] = list(" " * 18)
    buf[300] = especie
    buf[301:401] = list(" " * 100)
    buf[401:403] = list("01")
    buf[403:407] = list(indexador)
    buf[407:417] = list(vcp_tipo_field)
    buf[417:422] = list(taxa_field)
    spread_field = " " * 8
    raw_spread = (taxa_spread_val or "").replace(",", ".").strip()
    if raw_spread:
        try:
            dec_spread = Decimal(raw_spread).quantize(Decimal("0.0001"), rounding=ROUND_DOWN)
            spread_field = str(int(dec_spread * 10000)).rjust(8, "0")
        except InvalidOperation:
            raise ValueError(f"TAXA_SPREAD inválida: '{raw_spread}'")
    buf[422:430] = list(spread_field)
    buf[430:432] = list(crit_field)
    buf[432] = "N"
    buf[433:467] = list(" " * 34)
    buf[467] = "N"
    nome_emissor = clean_text_field((nome_emissor_val or "").strip())
    if not nome_emissor:
        raise ValueError("NOME_EMISSOR é obrigatório")
    buf[468:518] = list(nome_emissor[:50].ljust(50))
    cnpj = re.sub(r"\D", "", (cnpj_emissor_val or ""))
    if not cnpj:
        raise ValueError("CNPJ_EMISSOR é obrigatório")
    buf[518:532] = list(cnpj.rjust(14, "0"))
    buf[532:553] = list(" " * 21)

    line = "".join(buf)
    if len(line) != NC_LEN:
        raise ValueError(f"Registro NC inválido: {len(line)} (esperado {NC_LEN})")
    return line

# =========================
# Escrita do arquivo
# =========================
def write_txt(lines: list[str], out_path: str | Path = "REMESSA.txt") -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        for line in lines:
            f.write(line.rstrip("\r\n") + "\r\n")
    return out_path

# =========================
# Main (sem pop-ups)
# =========================
def main(arquivo_saida: str | Path | None = None,
         caminho_entrada: str | Path | None = None,
         sheet_index: int | None = None) -> None:
    """
    Sem messagebox: comunica via prints/exception (para o launcher capturar).
    """
    # Se falhar, vamos propagar exceções (sem pop-up)
    if caminho_entrada is not None:
        path = Path(caminho_entrada)
    else:
        path = choose_file()

    df = read_any_table(path, sheet_index=sheet_index)
    df = normalize_columns(df)

    required = {
        "DATA_DE_EMISSAO",
        "DATA_DE_VENCIMENTO",
        "QUANTIDADE_EMITIDA",
        "VALOR_UNITARIO",
        "INDEXADOR",
        "TAXA_SPREAD",
        "NOME_EMISSOR",
        "CNPJ_EMISSOR",
    }
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"Colunas obrigatórias ausentes: {', '.join(missing)}")

    header = build_header()
    lines = [header]

    for idx, row in df.iterrows():
        try:
            nc_line = build_nc(
                row.get("DATA_DE_EMISSAO", ""),
                row.get("DATA_DE_VENCIMENTO", ""),
                row.get("QUANTIDADE_EMITIDA", ""),
                row.get("VALOR_UNITARIO", ""),
                row.get("AVALISTA", ""),
                row.get("ESPECIE/GARANTIA", ""),
                row.get("INDEXADOR", ""),
                row.get("TIPO_INDICADOR_VCP", ""),
                row.get("TAXA_FLUTUANTE", ""),
                row.get("CRITERIO_CALCULO_JUROS", ""),
                row.get("TAXA_SPREAD", ""),
                row.get("NOME_EMISSOR", ""),
                row.get("CNPJ_EMISSOR", ""),
            )
            lines.append(nc_line)
        except Exception as e:
            raise ValueError(f"Erro ao montar NC na linha {idx + 2} da planilha: {e}")

    if arquivo_saida:
        out = write_txt(lines, Path(arquivo_saida))
    else:
        out = write_txt(lines, Path(path).parent / "REMESSA.txt")

    # Sem pop-up: apenas prints (para o launcher ler, se quiser)
    print(f"Arquivo gerado: {out.resolve()}")
    print(f"Registros NC gerados: {len(lines) - 1}")

if __name__ == "__main__":
    main()
