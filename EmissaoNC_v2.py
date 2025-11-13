# EmissaoNC_v2.py
from __future__ import annotations
import datetime as dt
from pathlib import Path
import unicodedata
import re
import pandas as pd
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from tkinter import Tk, filedialog  # sem messagebox

# =========================
# Constantes de Header/NC
# =========================
HEADER_PREFIX = "NC   0INCLLIMINETRUSTDTVM     "
HEADER_SUFFIX = "00004<"
HEADER_LEN = 44

NC_PREFIX = "NC   1INCL              0000"
NC_LEN = 553

FORMATO_EMISSAO_FIXO = "E"  # pos 38 (indice 37)
TIPO_REGIME_FIXO = "2"      # pos 185 (indice 184)
EVENTOS_CURSADOS_FIXO = "N"  # pos 186 (indice 185)
CONTA_EMISSOR_REGISTRADOR = "33738404"
CONTA_ESCRITURADOR = "33738002"
NUMERO_EMISSAO_FIXO = "1"
NUMERO_SERIE_FIXO = "1"
TIPO_EMISSAO_FIXO = "N"
FORMA_PAGAMENTO_DEFAULT = "01"
INCORPORA_JUROS_DEFAULT = "N"
PUBLICO_OFERTA_DEFAULT = " "
RITO_OFERTA_DEFAULT = " "
PENDENTE_DEMO_DEFAULT = "N"
PERIODICIDADE_JUROS_DEFAULT = " "
UNIDADE_JUROS_DEFAULT = " "
TIPO_PRAZO_DEFAULT = " "

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
# Selecao e leitura da planilha
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
        raise SystemExit("Nenhum arquivo selecionado.")
    return Path(path)


def read_any_table(path: Path, sheet_index: int | None = None) -> pd.DataFrame:
    suffix = path.suffix.lower()
    idx = SHEET_INDEX if sheet_index is None else sheet_index
    if suffix in {".xlsx", ".xlsm", ".xltx", ".xltm"}:
        xls = pd.ExcelFile(path, engine="openpyxl")
        sheet_names = xls.sheet_names
        if isinstance(idx, int):
            if idx >= len(sheet_names):
                idx = 0
            sheet_name = sheet_names[idx]
        else:
            sheet_name = idx
        df = xls.parse(sheet_name=sheet_name, dtype=object)
    elif suffix == ".csv":
        df = pd.read_csv(path, dtype=object, sep=",", encoding="utf-8", keep_default_na=True)
    else:
        raise ValueError(f"Formato nao suportado: {suffix} (aceitos: .xlsx, .xlsm, .xltx, .xltm, .csv)")

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
# Datas e validacoes
# =========================
def build_header(date: dt.date | None = None) -> str:
    d = date or dt.date.today()
    header = f"{HEADER_PREFIX}{d.strftime('%Y%m%d')}{HEADER_SUFFIX}"
    if len(header) != HEADER_LEN:
        raise ValueError(f"Header invalido: {len(header)} (esperado {HEADER_LEN})")
    return header


def normalize_date_any(value, field_name: str) -> str:
    if isinstance(value, (dt.datetime, dt.date, pd.Timestamp)):
        if isinstance(value, dt.datetime):
            value = value.date()
        return value.strftime("%Y%m%d")

    if isinstance(value, (int, float)) and not pd.isna(value):
        try:
            base = pd.Timestamp('1899-12-30')
            ts = base + pd.to_timedelta(float(value), unit='D')
            return ts.strftime('%Y%m%d')
        except Exception:
            pass

    s = (str(value or "").strip())
    if not s:
        raise ValueError(f"{field_name} ausente")

    if re.search(r"[^\d]", s):
        ts = pd.to_datetime(s, errors="coerce", dayfirst=True)
        if pd.isna(ts):
            ts = pd.to_datetime(s, errors="coerce", dayfirst=False)
        if not pd.isna(ts):
            return ts.strftime("%Y%m%d")
        if '/' in s:
            try:
                return dt.datetime.strptime(s, '%d/%m/%Y').strftime('%Y%m%d')
            except ValueError:
                pass
            try:
                return dt.datetime.strptime(s, '%Y/%m/%d').strftime('%Y%m%d')
            except ValueError:
                pass

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

    raise ValueError(f"Data invalida (informe AAAAMMDD, ex.: 20250903): '{s}'")


def days_diff_yyyymmdd(start_yyyymmdd: str, end_yyyymmdd: str) -> int:
    d1 = dt.datetime.strptime(start_yyyymmdd, "%Y%m%d").date()
    d2 = dt.datetime.strptime(end_yyyymmdd, "%Y%m%d").date()
    if d2 < d1:
        raise ValueError("DATA_DE_VENCIMENTO anterior a DATA_DE_EMISSAO")
    return (d2 - d1).days

# =========================
# Mapas e parsers especificos
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
    raise ValueError("INDEXADOR invalido/ausente (use VCP, SELIC, DI, TR ou PRE-FIXADO)")


FORMAS_EXIGEM_FLUXO = {"02", "03", "04"}




def parse_forma_pagamento(value: str) -> str:
    s = re.sub(r"\D", "", str(value or ""))
    if not s:
        s = FORMA_PAGAMENTO_DEFAULT
    s = s.zfill(2)[-2:]
    if s not in {"01", "02", "03", "04", "05", "06", "07"}:
        raise ValueError("FORMA_PAGAMENTO invalida (use 01..07)")
    return s


def parse_flag_sn(value: str, field_name: str, default: str = "N", allow_blank: bool = False) -> str:
    s = (value or "").strip().upper()
    if not s:
        if allow_blank:
            return " "
        return default
    if s not in {"S", "N"}:
        raise ValueError(f"{field_name} deve ser 'S' ou 'N'")
    return s





def parse_decimal_field(value: str | Decimal, total_digits: int, decimal_places: int, field_name: str) -> str:
    raw = (str(value).replace(',', '.') if value not in {None, ''} else '').strip()
    if not raw:
        raise ValueError(f"{field_name} ausente")
    try:
        dec = Decimal(raw)
    except InvalidOperation:
        raise ValueError(f"{field_name} invalido: '{value}'")
    quant = Decimal(f"1e-{decimal_places}")
    dec = dec.quantize(quant, rounding=ROUND_DOWN)
    scaled = int(dec * (10 ** decimal_places))
    width = total_digits + decimal_places
    return str(scaled).rjust(width, "0")


def parse_periodicidade(value: str) -> str:
    s = (value or "").strip().upper()
    if not s:
        return PERIODICIDADE_JUROS_DEFAULT
    if s not in {"C", "V"}:
        raise ValueError("PERIODICIDADE_JUROS invalida (use C ou V)")
    return s


def parse_unidade_juros(value: str) -> str:
    s = (value or "").strip().upper()
    if not s:
        return UNIDADE_JUROS_DEFAULT
    if s not in {"D", "U", "M"}:
        raise ValueError("UNIDADE invalida (use D, U ou M)")
    return s


def parse_tipo_prazo(value: str) -> str:
    s = (value or "").strip().upper()
    if not s:
        return TIPO_PRAZO_DEFAULT
    if s not in {"U", "C"}:
        raise ValueError("TIPO_PRAZO invalido (use U ou C)")
    return s


def parse_intervalo_juros(value: str, field_name: str) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    # Permite campo em branco: retorna 10 espaços quando não houver dígitos
    if not digits:
        return " " * 10
    if len(digits) > 10:
        raise ValueError(f"{field_name} deve ter ate 10 digitos")
    return digits.zfill(10)


def map_criterio_calc_juros(v: str) -> str:
    """Mapeia o valor da planilha para o código de critério de cálculo de juros.

    Regras de robustez aplicadas:
    - Aceita diretamente códigos "01".."06".
    - Ignora acentos e variações de espaço/hífen.
    - Aceita descrições com e sem acento (compatível com versões antigas de planilhas).
    """
    raw = (v or "").strip()
    # Excel às vezes exibe/aplica um apóstrofo inicial para forçar texto. Se vier no CSV como caractere literal,
    # removemos aspas/apóstrofos nas extremidades para não atrapalhar o parse.
    raw = raw.strip("'\"`")
    if not raw:
        return ""

    # Se vier como código numérico
    # 1) Apenas 1-2 dígitos
    m_exact = re.match(r"^\s*0?([1-6])\s*$", raw)
    if m_exact:
        return m_exact.group(1).zfill(2)
    # 2) Código no início seguido de texto
    m_prefix = re.match(r"^\s*0?([1-6])\b", raw)
    if m_prefix:
        return m_prefix.group(1).zfill(2)

    # Normaliza acentos, caixa e espaços/hífens
    s = _strip_accents_upper(raw)
    s = re.sub(r"\s+", " ", s)
    s = s.replace(" – ", "-").replace(" - ", "-").replace("–", "-")

    mapping = {
        "252-NUMERO DIAS UTEIS ENTRE A DATA DE INICIO OU O ULTIMO PAGAMENTO E O PROXIMO": "01",
        "252-NUMERO DE MESES ENTRE A DATA DE INICIO OU O ULTIMO PAGAMENTO E O PROXIMO X 21": "02",
        "360-NUMERO DIAS CORRIDOS ENTRE A DATA DE INICIO OU O ULTIMO PAGAMENTO E O PROXIMO": "03",
        "360-NUMERO DE MESES ENTRE A DATA DE INICIO OU O ULTIMO PAGAMENTO E O PROXIMO X 30": "04",
        "365-NUMERO DIAS CORRIDOS ENTRE A DATA DE INICIO OU O ULTIMO PAGAMENTO E O PROXIMO": "05",
        # Algumas planilhas antigas nao trazem "ULTIMO PAGAMENTO E" nesta ultima linha
        "365-NUMERO DE MESES ENTRE A DATA DE INICIO OU O PROXIMO X 30": "06",
        # Versoes com acentos (apos normalizacao acima, viram estas chaves):
        "252-NUMERO DIAS UTEIS ENTRE A DATA DE INICIO OU O ULTIMO PAGAMENTO E O PROXIMO": "01",
        "252-NUMERO DE MESES ENTRE A DATA DE INICIO OU ULTIMO PAGAMENTO E O PROXIMO X 21": "02",
        "360-NUMERO DIAS CORRIDOS ENTRE A DATA DE INICIO OU ULTIMO PAGAMENTO E O PROXIMO": "03",
        "360-NUMERO DE MESES ENTRE A DATA DE INICIO OU ULTIMO PAGAMENTO E O PROXIMO X 30": "04",
        "365-NUMERO DIAS CORRIDOS ENTRE A DATA DE INICIO OU ULTIMO PAGAMENTO E O PROXIMO": "05",
        "365-NUMERO DE MESES ENTRE A DATA DE INICIO OU PROXIMO X 30": "06",
    }
    return mapping.get(s, "")

# =========================
# Montagem do registro NC (versao 2)
# =========================
def build_nc_v2(
    data_emissao,
    data_vencimento,
    qtd_emitida,
    valor_unitario,
    avalista_val,
    especie_garantia_val,
    indexador_val,
    tipo_indicador_vcp_val,
    taxa_flu_val,
    criterio_val,
    taxa_spread_val,
    nome_emissor_val,
    cnpj_emissor_val,
    forma_pagamento_val,
    incorpora_juros_val,
    data_incorporacao_juros_val,
    valor_apos_incorporacao_val,
        periodicidade_juros_val,
    juros_a_cada_val,
    unidade_juros_val,
    tipo_prazo_val,
    data_a_partir_juros_val,
):
    de = normalize_date_any(data_emissao, "DATA_DE_EMISSAO")
    dv = normalize_date_any(data_vencimento, "DATA_DE_VENCIMENTO")
    diff_str = str(days_diff_yyyymmdd(de, dv)).rjust(10, "0")

    qtd_str = re.sub(r"\D+", "", str(qtd_emitida or "").strip())
    if qtd_str == "":
        raise ValueError("QUANTIDADE_EMITIDA ausente ou invalida")
    qtd_str = str(int(qtd_str)).rjust(10, "0")

    try:
        dec_unit = Decimal(str(valor_unitario).replace(',', '.'))
    except InvalidOperation:
        raise ValueError(f"VALOR_UNITARIO invalido: '{valor_unitario}'")
    dec_unit = dec_unit.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
    valor_unit_str = str(int(dec_unit * (10 ** 8))).rjust(24, "0")

    valor_fin = (Decimal(qtd_str) * dec_unit).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    valor_fin_str = str(int(valor_fin * 100)).rjust(12, "0")

    avalista = clean_text_field(re.sub(r"\s+", " ", (avalista_val or "").strip()) or "NAO HA")
    avalista_field = avalista[:50].ljust(50)

    especie = map_especie_garantia(especie_garantia_val or "")
    indexador = map_indexador(indexador_val or "")

    vcp_tipo_field = " " * 10
    if indexador == "0000":
        nums = re.sub(r"\D", "", (tipo_indicador_vcp_val or "").strip())
        if nums == "":
            raise ValueError("TIPO_INDICADOR_VCP obrigatorio quando INDEXADOR=VCP")
        vcp_tipo_field = nums.rjust(10, "0")

    taxa_field = " " * 5
    if indexador in {"0001", "0003", "0000"}:
        raw = (taxa_flu_val or "").replace(',', '.').strip()
        if raw:
            tdec = Decimal(raw).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
            taxa_field = str(int(tdec * 100)).rjust(5, "0")
        elif indexador in {"0001", "0003"}:
            raise ValueError("TAXA_FLUTUANTE obrigatoria para INDEXADOR=SELIC/DI")

    crit_field = " " * 2
    if taxa_field.strip():
        code = map_criterio_calc_juros(criterio_val or "")
        if code not in {"01", "02", "03", "04", "05", "06"}:
            raise ValueError(f"CRITERIO_CALCULO_JUROS invalido/ausente (recebido='{criterio_val}')")
        crit_field = code

    tipo_emissao = TIPO_EMISSAO_FIXO
    forma_pagamento = parse_forma_pagamento(forma_pagamento_val)

    if forma_pagamento in FORMAS_EXIGEM_FLUXO:
        raw_incorp = (incorpora_juros_val or "").strip()
        if not raw_incorp:
            raise ValueError("INCORPORA_JUROS obrigatorio para forma de pagamento 02, 03 ou 04")
        incorpora_juros = parse_flag_sn(incorpora_juros_val, "INCORPORA_JUROS", default=INCORPORA_JUROS_DEFAULT)
    else:
        incorpora_juros = " "

    if incorpora_juros == "S":
        data_incorp = normalize_date_any(data_incorporacao_juros_val, "DATA_INCORPORACAO_JUROS")
        valor_pos_incorp = parse_decimal_field(
            valor_apos_incorporacao_val, total_digits=16, decimal_places=8, field_name="VALOR_APOS_INCORPORACAO"
        )
    else:
        data_incorp = " " * 8
        valor_pos_incorp = " " * 24

    publico_oferta = PUBLICO_OFERTA_DEFAULT
    rito_oferta = RITO_OFERTA_DEFAULT
    pend_demo = PENDENTE_DEMO_DEFAULT

    if forma_pagamento in FORMAS_EXIGEM_FLUXO:
        periodicidade = parse_periodicidade(periodicidade_juros_val)
        # Regra B3: "Juros a cada" (pos 534-543) é obrigatório somente quando periodicidade = Constante (C).
        # Quando periodicidade = Variável (V), o campo não deve ser preenchido (deve ficar em branco).
        if periodicidade == "V":
            juros_intervalo = " " * 10
        else:  # periodicidade C (Constante)
            juros_intervalo = parse_intervalo_juros(juros_a_cada_val, "JUROS_A_CADA")
            if not juros_intervalo.strip():
                raise ValueError("JUROS_A_CADA obrigatorio quando PERIODICIDADE_JUROS='C'")

        unidade_juros = parse_unidade_juros(unidade_juros_val)
        tipo_prazo = parse_tipo_prazo(tipo_prazo_val)
        data_a_partir = normalize_date_any(data_a_partir_juros_val, "DATA_A_PARTIR_JUROS")
    else:
        periodicidade = PERIODICIDADE_JUROS_DEFAULT
        juros_intervalo = " " * 10
        unidade_juros = UNIDADE_JUROS_DEFAULT
        tipo_prazo = TIPO_PRAZO_DEFAULT
        data_a_partir = " " * 8

    spread_field = " " * 8
    raw_spread = (taxa_spread_val or "").replace(',', '.').strip()
    if raw_spread:
        try:
            dec_spread = Decimal(raw_spread).quantize(Decimal("0.0001"), rounding=ROUND_DOWN)
            spread_field = str(int(dec_spread * 10000)).rjust(8, "0")
        except InvalidOperation:
            raise ValueError(f"TAXA_SPREAD invalida: '{raw_spread}'")

    buf = list(NC_PREFIX.ljust(NC_LEN, " "))
    buf[28] = tipo_emissao
    buf[29:37] = list(CONTA_EMISSOR_REGISTRADOR)
    buf[37] = FORMATO_EMISSAO_FIXO
    buf[38:46] = list(CONTA_ESCRITURADOR)
    buf[46:58] = list(" " * 12)
    buf[58] = NUMERO_EMISSAO_FIXO
    buf[59:62] = list(" ")
    buf[62:72] = list(NUMERO_SERIE_FIXO.ljust(10))
    buf[72:80] = list(de)
    buf[80:88] = list(dv)
    buf[88:98] = list(diff_str)
    today_str = dt.date.today().strftime("%Y%m%d")
    buf[98:106] = list(today_str)
    buf[106:116] = list(qtd_str)
    buf[116:140] = list(valor_unit_str)
    buf[140:152] = list(valor_fin_str)
    buf[152:184] = list(" " * 32)
    buf[184] = TIPO_REGIME_FIXO
    buf[185] = EVENTOS_CURSADOS_FIXO
    buf[186:216] = list("PRIVADA".ljust(30))
    buf[216:221] = list("2080".ljust(5))
    buf[221:229] = list("20231113")
    buf[229] = "S"
    buf[230] = " "
    buf[231:281] = list(avalista_field)
    buf[281] = parse_flag_sn("N", "CONTEM_AGENTE_FIDUCIARIO")
    buf[282:300] = list(" " * 18)
    buf[300] = especie
    buf[301:401] = list(" " * 100)
    buf[401:403] = list(forma_pagamento)
    buf[403:407] = list(indexador)
    buf[407:417] = list(vcp_tipo_field)
    buf[417:422] = list(taxa_field)
    buf[422:430] = list(spread_field)
    buf[430:432] = list(crit_field)
    buf[432] = incorpora_juros
    buf[433:441] = list(data_incorp)
    buf[441:465] = list(valor_pos_incorp)
    buf[465] = publico_oferta
    buf[466] = rito_oferta
    buf[467] = pend_demo
    nome_emissor = clean_text_field((nome_emissor_val or "").strip())
    if not nome_emissor:
        raise ValueError("NOME_EMISSOR e obrigatorio")
    buf[468:518] = list(nome_emissor[:50].ljust(50))
    cnpj = re.sub(r"\D", "", (cnpj_emissor_val or ""))
    if not cnpj:
        raise ValueError("CNPJ_EMISSOR e obrigatorio")
    buf[518:532] = list(cnpj.rjust(14, "0"))

    if forma_pagamento in FORMAS_EXIGEM_FLUXO:
        buf[532] = periodicidade
        buf[533:543] = list(juros_intervalo)
        buf[543] = unidade_juros
        buf[544] = tipo_prazo
        buf[545:553] = list(data_a_partir)
    else:
        buf[532:553] = list(" " * 21)

    line = "".join(buf)
    if len(line) != NC_LEN:
        raise ValueError(f"Registro NC invalido: {len(line)} (esperado {NC_LEN})")
    return line

# =========================
# Escrita do arquivo
# =========================
def write_txt(lines: list[str], out_path: str | Path = "REMESSA_v2.txt") -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        for line in lines:
            f.write(line.rstrip("\r\n") + "\r\n")
    return out_path

# =========================
# Main
# =========================
def main(arquivo_saida: str | Path | None = None, caminho_entrada: str | Path | None = None, sheet_index: int | None = None) -> None:
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
        "FORMA_PAGAMENTO",
        "INCORPORA_JUROS",
        "DATA_INCORPORACAO_JUROS",
        "VALOR_APOS_INCORPORACAO",

        "PERIODICIDADE_JUROS",
        "JUROS_A_CADA",
        "UNIDADE",
        "TIPO_PRAZO",
        "DATA_A_PARTIR_JUROS",
    }
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"Colunas obrigatorias ausentes: {', '.join(missing)}")

    header = build_header()
    lines = [header]

    for idx, row in df.iterrows():
        try:
            nc_line = build_nc_v2(
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
                row.get("FORMA_PAGAMENTO", ""),
                row.get("INCORPORA_JUROS", ""),
                row.get("DATA_INCORPORACAO_JUROS", ""),
                row.get("VALOR_APOS_INCORPORACAO", ""),
                                row.get("PERIODICIDADE_JUROS", ""),
                row.get("JUROS_A_CADA", ""),
                row.get("UNIDADE", ""),
                row.get("TIPO_PRAZO", ""),
                row.get("DATA_A_PARTIR_JUROS", ""),
            )
            lines.append(nc_line)
        except Exception as e:
            raise ValueError(f"Erro ao montar NC na linha {idx + 2} da planilha: {e}")

    if arquivo_saida:
        out = write_txt(lines, Path(arquivo_saida))
    else:
        out = write_txt(lines, Path(path).parent / "REMESSA_v2.txt")

    print(f"Arquivo gerado: {out.resolve()}")
    print(f"Registros NC gerados: {len(lines) - 1}")


if __name__ == "__main__":
    main()
