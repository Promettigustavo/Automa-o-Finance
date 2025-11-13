import requests
import json
import base64
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any
import logging

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURAÇÃO DE MÚLTIPLOS FUNDOS SANTANDER
# ============================================================
SANTANDER_FUNDOS = {
    "911_BANK": {
        "nome": "911 BANK MULTI ESTRATEGIA FUNDO DE INVESTIMENTO EM DIREITOS CREDITORIOS",
        "cnpj": "50.790.524/0001-00",
        "client_id": "3ZYICW0BDAwihhCwP4Tx08EtKYHFb2JG",
        "client_secret": "dAsx4AFNd7gNe8Lt",
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "AMPLIC": {
        "nome": "AMPLIC FUNDO DE INVESTIMENTO EM DIREITOS",
        "cnpj": "32.933.119/0001-03",
        "client_id": "ZcgN5NihardpebHHfewXrebGdnEH7dAk",  # ← Adicionar credenciais
        "client_secret": "qKapajRKdLXeTyGp",
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "CONDOLIVRE FIDC": {
        "nome": "CONDOLIVRE FUNDO DE INVESTIMENTO EM DIREITOS CREDITORIOS",
        "cnpj": "42.317.295/0001-74",
        "client_id": "WUrgXgftrP3G9iZXXIqljABiFx9oRBUC",
        "client_secret": "e4FAtyTG6mbDKPFV",
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "AUTO X": {
        "nome": "FUNDO DE INV EM DIREITOS CREDITORIOS CREDITAS AUTO X RESPONSABILIDADE LTDA",
        "cnpj": "53.095.241/0001-28",
        "client_id": "UWfbwD1F9TIaciza9vDMT9G2fAeOXK5x",  # ← Adicionar credenciais
        "client_secret": "FanZS0KOL3gIgpTy",
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "AUTO XI FIDC": {
        "nome": "FUNDO DE INVESTIMENTO EM DIREITOS CREDITORIOS CREDITAS AUTO XI",
        "cnpj": "58.035.124/0001-92",
        "client_id": "Ts21bGPsosCjh0SVeZrLDXefd0Tkn12Z",  # ← Adicionar credenciais
        "client_secret": "JwLavIQKYQlJDAeo",
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "TEMPUS III FIDC": {
        "nome": "FUNDO DE INVESTIMENTO EM DIREITOS CREDITORIOS NAO PADRONIZADOS CREDITAS TEMPUS III",
        "cnpj": "49.691.846/0001-04",
        "client_id": "7oyA8tfTt0lJTn04cPc5e7OMncoM0Ttw",  # ← Adicionar credenciais
        "client_secret": "Q08pRGWaP1paZy70",
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "INOVA": {
        "nome": "INOVA CREDITECH III FIDC SEGMENTO MULTICARTEIRA DE RESPONSABILIDADE LIMITADA",
        "cnpj": "52.340.225/0001-90",
        "client_id": "SkCHkZ4HTqVh33FAdXVolhOKBhJo8Ccf",  # ← Adicionar credenciais
        "client_secret": "G3Adg7yMsVnW4fT2",
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "MAKENA": {
        "nome": "MAKENA FUNDO DE INVESTIMENTO EM DIREITOS CREDITORIOS NAO PADRONIZADO",
        "cnpj": "45.938.235/0001-67",
        "client_id": "6RYSAWrbfS5oGKvGfIom7gyemqZDtGmu",  # ← Adicionar credenciais
        "client_secret": "Gl7x4FzaAyb4j2w6",
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "SEJA": {
        "nome": "SEJA FUNDO DE INVESTIMENTO EM DIREITOS CREDITORIOS",
        "cnpj": "24.987.402/0001-90",
        "client_id": "AUkiz79AzIzOWCmrPlTJG1mrallQDGTj",  # ← Adicionar credenciais
        "client_secret": "2GYZYfWZMb0TVm4O",
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "AKIREDE": {
        "nome": "AKI REDE FUNDO DE INVESTIMENTO EM DIREITOS CREDITORIOS",
        "cnpj": "52.200.745/0001-06",
        "client_id": "jGodGw5UYmHFN2AfUDrjn59rQ3rfG8ii",  # ← Adicionar credenciais
        "client_secret": "e3m9ALPlFJ3CImWy",
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "ATICCA": {
        "nome": "ATICCA DIGITAL FUNDO DE INVESTIMENTO EMDIREITOS CREDITORIOS",
        "cnpj": "47.425.860/0001-30",
        "client_id": "jAn2GjinMON6PqGe1Xd55AtGMEEEMNzk",  # ← Adicionar credenciais
        "client_secret": "BKCAUBHAhYmjG6sC",
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "ALTLEGAL": {
        "nome": "ALT LEGAL CLAIMS FUNDO DE INVESTIMENTO EM DIREITOS CREDITORIOS",
        "cnpj": "59.111.770/0001-54",
        "client_id": "yh8d7AxCeAczNx9JCGlDNfhi6UAbjJ3W",  # ← Adicionar credenciais
        "client_secret": "tYv3gv1OHpG9VGmw",
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "NETMONEY": {
        "nome": "NETMONEY FUNDO DE INVESTIMENTO EM DIREITOS CREDITORIOS",
        "cnpj": "50.824.501/0001-60",
        "client_id": "khml0Jbohydfk8Y4wVIfAUN3odLR8g0Y",  # ← Adicionar credenciais
        "client_secret": "5phosEtGQUal385F",
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "TCG": {
        "nome": "TCG FUNDO DE INVESTIMENTO EM DIREITOS CREDITORIOS",
        "cnpj": "58.304.663/0001-80",
        "client_id": "t8pceOLapDsFJ6AElE82cNyG1lfYFS0m",  # ← Adicionar credenciais
        "client_secret": "3s4HeOVhpJvkf7iw",
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "DORO": {
        "nome": "D'ORO CAPITAL FUNDO DE INVESTIMENTO EM DIREITOS CREDITORIOSMULTISSETORIAL",  # ← Adicionar nome completo do fundo
        "cnpj": "51.731.270/0001-03",  # ← Adicionar CNPJ
        "client_id": "FXA6APtdbJswLzEuDfHT19ZwiCZQgEzK",  # ← Adicionar Client ID
        "client_secret": "rGgUx8ceBVHfC0Cu",  # ← Adicionar Client Secret
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "ORION": {
        "nome": "ORION JN FUNDO DE INV EM DIREITOS CREDITORIOS NAO-PADRONIZADOS MULTISSETORIAL",  # ← Adicionar nome completo do fundo
        "cnpj": "38.057.973/0001-30",  # ← Adicionar CNPJ
        "client_id": "quT8mOWAhnDy98453Z2T7QxAK9dkLhNq",  # ← Adicionar Client ID
        "client_secret": "MZ7yzwAGfwhaA9P0",  # ← Adicionar Client Secret
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "AGA": {
        "nome": "AGA FUNDO DE INV EM DIREITOS CREDITORIOSNAO-PADRONIZADOS MULTISSETORIAL",  # ← Adicionar nome completo do fundo
        "cnpj": "24.080.647/0001-39",  # ← Adicionar CNPJ
        "client_id": "cOHqYxoQCrMmsvFpGU9PC936GYzg2PBW",  # ← Adicionar Client ID
        "client_secret": "D5j2RAKM8ESJDd8g",  # ← Adicionar Client Secret
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "PRIME": {
        "nome": "PRIME FUNDO DE INVESTIMENTO EM DIREITOSCREDITORIOS MULTISSETORIAL",  # ← Adicionar nome completo do fundo
        "cnpj": "20.905.862/0001-70",  # ← Adicionar CNPJ
        "client_id": "Qpb96NXSyle6ojA6roTMupt8U2CPdEiT",  # ← Adicionar Client ID
        "client_secret": "Au4FnnIw1DloVEdl",  # ← Adicionar Client Secret
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "ALBATROZ": {
        "nome": "ALBATROZ FUNDO DE INVESTIMENTO EM DIREITOS CREDITORIOS MULTISSETORIAL",  # ← Adicionar nome completo do fundo
        "cnpj": "25.354.081/0001-59",  # ← Adicionar CNPJ
        "client_id": "yIuAU7uhe93PTGdRrbLAU0x7HGZXbVCU",  # ← Adicionar Client ID
        "client_secret": "Uj8YINjcSc4MapGB",  # ← Adicionar Client Secret
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "TESLA": {
        "nome": "TESLA FUNDO DE INVESTIMENTO EM DIREITOS CREDITORIOS MULTISSETORIAL",
        "cnpj": "51.732.995/0001-16",  # ← Adicionar CNPJ
        "client_id": "MD1dFLBv62AV8tAioBgiHwU2F0h8XGDH",  # ← Adicionar Client ID
        "client_secret": "zJUMHBNP6SaW4ntA",  # ← Adicionar Client Secret
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "ALTINVEST": {
        "nome": "ALTINVEST FUNDO DE INVESTIMENTO EM DIREITOS CREDITORIOS",
        "cnpj": "58.888.944/0001-27",  # ← Adicionar CNPJ
        "client_id": "ieHHqhhTfLSJGrGAwKtgF1zaiQMRD97v",  # ← Adicionar Client ID
        "client_secret": "ZcCXPG5z6IRD8ofY",  # ← Adicionar Client Secret
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "ANTARES": {
        "nome": "ANTARES FUNDO DE INVESTIMENTO EM DIREITOS CREDITORIOS",
        "cnpj": "60.078.440/0001-93",  # ← Adicionar CNPJ
        "client_id": "RAOBLb4L3M7jkAA0GNUjTh14GnwOA37R",  # ← Adicionar Client ID
        "client_secret": "cHG1lRMIVfnhg8yV",  # ← Adicionar Client Secret
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "AV_CAPITAL": {
        "nome": "AV CAPITAL FUNDO DE INVESTIMENTO EM DIREITOS CREDITORIOS",
        "cnpj": "51.313.788/0001-27",  # ← Adicionar CNPJ
        "client_id": "BpmDhrmwNaq70IIeXJwH1hdnKtFSLAF8",  # ← Adicionar Client ID
        "client_secret": "StnmdhBpSA7nUmFi",  # ← Adicionar Client Secret
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "BAY": {
        "nome": "BAY FUNDO DE INVESTIMENTO EM DIREITOS CREDITORIOS",
        "cnpj": "60.252.007/0001-22",  # ← Adicionar CNPJ
        "client_id": "dAfbuCpzagckdr5rg6DAI3aH8z8u1v6N",  # ← Adicionar Client ID
        "client_secret": "Fu6uJXmJIbGl9qWG",  # ← Adicionar Client Secret
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "BLIPS": {
        "nome": "BLIPS FUNDO DE INVESTIMENTO EM DIREITOS CREDITORIOS - RESPONSABILIDADE LIMITADA",
        "cnpj": "58.482.694/0001-20",  # ← Adicionar CNPJ
        "client_id": "r4tqPLeZmomOjhuvroPQs94LZpAHp89H",  # ← Adicionar Client ID
        "client_secret": "vaHpJNjsujpI34Yp",  # ← Adicionar Client Secret
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "COINVEST_COTAS": {
        "nome": "COINVEST FUNDO DE INV EM COTAS DE FUNDOS DE INVESTIMENTO EM DIREITOS CREDITORIOS",
        "cnpj": "",  # ← Adicionar CNPJ
        "client_id": "",  # ← Adicionar Client ID
        "client_secret": "",  # ← Adicionar Client Secret
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "COINVEST": {
        "nome": "COINVEST FUNDO DE INVESTIMENTO EM DIREITOS CREDITORIOS",
        "cnpj": "39.851.520/0001-43",  # ← Adicionar CNPJ
        "client_id": "ejgMPY9vkeOAVQoIEJGDGNsxLCojLUxA",  # ← Adicionar Client ID
        "client_secret": "o5oA6kMGbHGTxjKj",  # ← Adicionar Client Secret
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "EXT_LOOMY": {
        "nome": "EXT LOOMY FUNDO DE INVESTIMENTO EM DIREITOS CREDITORIOS RESPONSABILIDADE LTDA",
        "cnpj": "61.062.538/0001-15",  # ← Adicionar CNPJ
        "client_id": "kELiN4rMxRGvT87lGlgTjUsWKGqptAJz",  # ← Adicionar Client ID
        "client_secret": "LjNwu84IrYAFQ2Yw",  # ← Adicionar Client Secret
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "CONSORCIEI": {
        "nome": "FUNDO DE INV EM COTAS DE FUNDOS DE INV EM DIREITOS CREDITORIOS CONSORCIEI 0",
        "cnpj": "60.115.778/0001-78",  # ← Adicionar CNPJ
        "client_id": "9Koio458B0Ldmj22KIPGBaaCQTVXXkNt",  # ← Adicionar Client ID
        "client_secret": "AU8Sz6s6HBPWsu3V",  # ← Adicionar Client Secret
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "IGAPORA": {
        "nome": "IGAPORA FUNDO DE INV EM COTAS DE FUNDOS DE INV MULTIMERCADO CREDIT PRIVADO LIVRE",
        "cnpj": "51.861.413/0001-00",  # ← Adicionar CNPJ
        "client_id": "SNSIPz2vPflTpGG4mXsV2wiyKYA9tqDB",  # ← Adicionar Client ID
        "client_secret": "CdsEomBNz2sg4uqU",  # ← Adicionar Client Secret
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "LAVOURA": {
        "nome": "LAVOURA FIAGRO - DIREITOS CREDITORIOS",
        "cnpj": "61.007.751/0001-24",  # ← Adicionar CNPJ
        "client_id": "GE4Tk4OwrHeSR09zdWGHQhr5qvBoc4Qt",  # ← Adicionar Client ID
        "client_secret": "9ixjmnlRfYGWUDnR",  # ← Adicionar Client Secret
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "MACAUBAS": {
        "nome": "MACAUBAS FUNDO DE INVESTIMENTO EM PARTICIPACOES MULTIESTRATEGIA",
        "cnpj": "56.960.033/0001-38",  # ← Adicionar CNPJ
        "client_id": "FpikkANTNekz9woA7ix942j71EAqcufB",  # ← Adicionar Client ID
        "client_secret": "978wwHvAWOdEnUsU",  # ← Adicionar Client Secret
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "MARCA I": {
        "nome": "MARCA I FUNDO DE INVESTIMENTO EM DIREITOS CREDITORIOS NAO PADRONIZADO",
        "cnpj": "49.466.992/0001-36",  # ← Adicionar CNPJ
        "client_id": "N3PPK8MGGaY5IYhu2AbwNAhwabcwaK0c",  # ← Adicionar Client ID
        "client_secret": "gdyqcXgSUkEPkSxl",  # ← Adicionar Client Secret
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "NX_BOATS": {
        "nome": "NX BOATS FUNDO DE INVESTIMENTO EM DIREITOS CREDITORIOS",
        "cnpj": "61.430.639/0001-00",  # ← Adicionar CNPJ
        "client_id": "32TKKJOIEAIepS3fwJ3jA2V8SZLKZALC",  # ← Adicionar Client ID
        "client_secret": "1T41mC3gzIKNoMek",  # ← Adicionar Client Secret
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "OKLAHOMA": {
        "nome": "OKLAHOMA FUNDO DE INVESTIMENTO EM DIREITOS CREDITORIOS",
        "cnpj": "57.976.577/0001-50",  # ← Adicionar CNPJ
        "client_id": "xAytHPeZuujFPGhaEqn1tAYtq2JWXnxs",  # ← Adicionar Client ID
        "client_secret": "wCBd6OuAUK9UXeer",  # ← Adicionar Client Secret
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "ONCRED": {
        "nome": "ONCRED FUNDO DE INVESTIMENTO EM DIREITOS CREDITORIOS",
        "cnpj": "60.368.384/0001-21",  # ← Adicionar CNPJ
        "client_id": "TwndCMBA7DelsmPTeRKaRMfxR9bTQtq7",  # ← Adicionar Client ID
        "client_secret": "1gt8ZQ1Gs7ZqcfCq",  # ← Adicionar Client Secret
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "ORIZ_JUS_CPS": {
        "nome": "ORIZ JUS CPS FUNDO DE INVESTIMENTO EM DIREITOS CREDITORIOS",
        "cnpj": "61.543.748/0001-25",  # ← Adicionar CNPJ
        "client_id": "gBl3S9CXD6e9qWjMVrGAG8FocE6MGI90",  # ← Adicionar Client ID
        "client_secret": "x8hevWrq6IcdkoDL",  # ← Adicionar Client Secret
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "SIM": {
        "nome": "SIM FUNDO DE INVESTIMENTO EM DIREITOS CREDITORIOS",
        "cnpj": "60.681.487/0001-47",  # ← Adicionar CNPJ
        "client_id": "3ZAxFOOtrIYC1b6N46NGwRQ410yEsIO1",  # ← Adicionar Client ID
        "client_secret": "SyxpmEOUvCqBgHjn",  # ← Adicionar Client Secret
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "SYMA": {
        "nome": "SYMA FUNDO DE INVESTIMENTO FINANCEIRO MULTIMERCADO",
        "cnpj": "60.232.226/0001-40",  # ← Adicionar CNPJ
        "client_id": "Qrh2Frwdz6gAKLdIqzcMIGjd7HWsS6tD",  # ← Adicionar Client ID
        "client_secret": "Ql6cMGC8OLHJxh6X",  # ← Adicionar Client Secret
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    },
    "YUNUS": {
        "nome": "YUNUS NEGOCIOS SOCIAIS FUNDO DE INVESTIMENTO EM DIREITOS CREDITORIOS",
        "cnpj": "29.330.482/0001-20",  # ← Adicionar CNPJ
        "client_id": "HdkMM1v16AKGRwhZsjG3qTG8dXaccUQL",  # ← Adicionar Client ID
        "client_secret": "I8eMkGnnasdsLoXE",  # ← Adicionar Client Secret
        "cert_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem",
        "key_path": "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"
    }
}

class SantanderAuth:
    """
    Classe para gerenciar autenticação Client Credentials com API Santander
    Usa certificado mTLS + client_id + client_secret
    Suporta múltiplos fundos através do parâmetro fundo_id
    """
    
    @classmethod
    def criar_por_fundo(cls, fundo_id: str, ambiente: str = "producao"):
        """
        Cria uma instância de SantanderAuth a partir do ID do fundo
        
        Args:
            fundo_id: ID do fundo (chave do dicionário SANTANDER_FUNDOS)
            ambiente: 'sandbox' ou 'producao'
        
        Returns:
            Instância de SantanderAuth configurada para o fundo
        """
        if fundo_id not in SANTANDER_FUNDOS:
            raise ValueError(f"Fundo '{fundo_id}' não encontrado. Fundos disponíveis: {list(SANTANDER_FUNDOS.keys())}")
        
        config = SANTANDER_FUNDOS[fundo_id]
        
        if not config["client_id"] or not config["client_secret"]:
            raise ValueError(f"Fundo '{fundo_id}' não tem credenciais configuradas")
        
        logger.info(f"Criando autenticação para fundo: {config['nome']}")
        logger.info(f"CNPJ: {config['cnpj']}")
        
        return cls(
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            cert_path=config["cert_path"],
            key_path=config.get("key_path"),
            ambiente=ambiente,
            fundo_id=fundo_id,
            fundo_nome=config["nome"],
            fundo_cnpj=config["cnpj"]
        )
    
    def __init__(self, client_id: str, client_secret: str, 
                 cert_path: str, key_path: str = None, ambiente: str = "producao",
                 fundo_id: str = None, fundo_nome: str = None, fundo_cnpj: str = None):
        """
        Inicializa o cliente de autenticação Santander
        
        Args:
            client_id: X-Application-Key fornecido pelo Santander
            client_secret: Client Secret fornecido pelo Santander
            cert_path: Caminho para o certificado .PEM (obrigatório para mTLS)
            key_path: Caminho para a chave privada .PEM (se separada do certificado)
            ambiente: 'sandbox' ou 'producao'
            fundo_id: ID do fundo (opcional)
            fundo_nome: Nome do fundo (opcional)
            fundo_cnpj: CNPJ do fundo (opcional)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.ambiente = ambiente
        self.fundo_id = fundo_id
        self.fundo_nome = fundo_nome
        self.fundo_cnpj = fundo_cnpj
        
        # Certificados para mTLS (obrigatório no Santander)
        self.cert_file = cert_path
        self.key_file = key_path
        
        if not cert_path:
            raise ValueError("Certificado é obrigatório para autenticação no Santander")
        
        logger.info(f"Certificado .PEM configurado: {cert_path}")
        
        # URLs base de acordo com o ambiente
        # Nota: API pode estar bloqueada ou inacessível via Internet pública
        self.base_urls = {
            "sandbox": {
                "token": "https://trust-open.api.santander.com.br/auth/oauth/v2/token",
                "api": "https://trust-open.api.santander.com.br"  # Usando mesmo domínio do token
            },
            "producao": {
                "token": "https://trust-open.api.santander.com.br/auth/oauth/v2/token",
                "api": "https://trust-open.api.santander.com.br"  # Usando mesmo domínio do token
            }
        }
        
        self.token_data = {
            "access_token": None,
            "token_type": None,
            "expires_in": None,
            "expires_at": None,
            "refresh_token": None
        }
        
        # Arquivo para armazenar o token (separado por fundo se tiver fundo_id)
        if self.fundo_id:
            self.token_file = Path(f"config/santander_token_{self.fundo_id}.json")
        else:
            self.token_file = Path("config/santander_token.json")
        
        self.token_file.parent.mkdir(exist_ok=True)
        
        # Carregar token salvo se existir
        self._load_token()
        
        if self.fundo_id:
            logger.info(f"✅ Autenticação configurada para: {self.fundo_nome}")
            logger.info(f"   CNPJ: {self.fundo_cnpj}")
            logger.info(f"   Token file: {self.token_file}")
    
    def _get_cert_tuple(self):
        """
        Retorna a tupla (cert, key) para uso com requests
        
        Returns:
            Tupla com caminho do certificado e chave, ou None se não configurado
        """
        if self.cert_file:
            if self.key_file:
                # Certificado e chave em arquivos separados
                return (self.cert_file, self.key_file)
            else:
                # Certificado e chave no mesmo arquivo
                return self.cert_file
        return None
    
    def _get_auth_header(self) -> str:
        """
        Cria o header de autenticação Basic (Base64 encoding de client_id:client_secret)
        
        Returns:
            String codificada em base64 para autenticação
        """
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"
    
    def _save_token(self):
        """Salva o token atual em arquivo JSON"""
        try:
            with open(self.token_file, 'w') as f:
                json.dump(self.token_data, f, indent=4)
            logger.info(f"Token salvo em {self.token_file}")
        except Exception as e:
            logger.error(f"Erro ao salvar token: {e}")
    
    def _load_token(self):
        """Carrega o token salvo do arquivo JSON"""
        try:
            if self.token_file.exists():
                with open(self.token_file, 'r') as f:
                    self.token_data = json.load(f)
                logger.info("Token carregado do arquivo")
        except Exception as e:
            logger.error(f"Erro ao carregar token: {e}")
    
    def _is_token_valid(self) -> bool:
        """
        Verifica se o token atual ainda é válido
        
        Returns:
            True se o token for válido, False caso contrário
        """
        if not self.token_data.get("access_token"):
            return False
        
        if not self.token_data.get("expires_at"):
            return False
        
        # Verifica se o token expira em mais de 5 minutos
        expires_at = datetime.fromisoformat(self.token_data["expires_at"])
        return datetime.now() + timedelta(minutes=5) < expires_at
    
    def obter_token_acesso(self) -> Dict[str, Any]:
        """
        Obtém token de acesso usando Client Credentials + certificado mTLS
        
        Returns:
            Dicionário com os dados do token
        """
        token_url = self.base_urls[self.ambiente]['token']
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Application-Key": self.client_id
        }
        
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        try:
            logger.info("Solicitando token de acesso ao Santander...")
            
            # Usa certificado mTLS (obrigatório)
            cert_tuple = self._get_cert_tuple()
            response = requests.post(
                token_url, 
                headers=headers, 
                data=data, 
                cert=cert_tuple,
                verify=True
            )
            
            response.raise_for_status()
            
            token_response = response.json()
            
            # Armazena os dados do token
            self.token_data = {
                "access_token": token_response.get("access_token"),
                "token_type": token_response.get("token_type", "Bearer"),
                "expires_in": token_response.get("expires_in"),
                "expires_at": (datetime.now() + timedelta(seconds=token_response.get("expires_in", 3600))).isoformat(),
                "refresh_token": token_response.get("refresh_token")
            }
            
            self._save_token()
            logger.info("Token de acesso obtido com sucesso!")
            
            return self.token_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao obter token: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Resposta do servidor: {e.response.text}")
            raise
    
    def get_token_info(self) -> Dict[str, Any]:
        """
        Retorna informações sobre o token atual
        
        Returns:
            Dicionário com informações do token
        """
        if not self.token_data.get("access_token"):
            return {"status": "Nenhum token disponível"}
        
        info = {
            "status": "Token disponível",
            "token_type": self.token_data.get("token_type"),
            "expires_at": self.token_data.get("expires_at"),
            "is_valid": self._is_token_valid()
        }
        
        return info


def listar_fundos_configurados():
    """
    Lista todos os fundos que têm credenciais configuradas
    
    Returns:
        Lista de tuplas (fundo_id, nome, cnpj, tem_credenciais)
    """
    fundos = []
    for fundo_id, config in SANTANDER_FUNDOS.items():
        tem_credenciais = bool(config["client_id"] and config["client_secret"])
        fundos.append({
            "id": fundo_id,
            "nome": config["nome"],
            "cnpj": config["cnpj"],
            "configurado": tem_credenciais
        })
    return fundos


def criar_auth_para_todos_fundos(ambiente: str = "producao"):
    """
    Cria instâncias de SantanderAuth para todos os fundos configurados
    
    Args:
        ambiente: 'sandbox' ou 'producao'
    
    Returns:
        Dicionário {fundo_id: SantanderAuth}
    """
    auth_clients = {}
    
    for fundo_id, config in SANTANDER_FUNDOS.items():
        if config["client_id"] and config["client_secret"]:
            try:
                auth_clients[fundo_id] = SantanderAuth.criar_por_fundo(fundo_id, ambiente)
                logger.info(f"✅ Auth criado para {fundo_id}")
            except Exception as e:
                logger.error(f"❌ Erro ao criar auth para {fundo_id}: {e}")
        else:
            logger.warning(f"⚠️ Fundo {fundo_id} sem credenciais - pulando")
    
    return auth_clients


# Exemplo de uso
if __name__ == "__main__":
    # ============================================================
    # CONFIGURAÇÃO - COLOQUE SUAS CREDENCIAIS AQUI
    # ============================================================
    CLIENT_ID = "WUrgXgftrP3G9iZXXIqljABiFx9oRBUC"      # ← X-Application-Key do Santander
    CLIENT_SECRET = "e4FAtyTG6mbDKPFV"                 # ← Client Secret do Santander
    
    # Certificado .PEM (OBRIGATÓRIO para API Santander)
    CERT_PEM_PATH = "C:\\Users\\GustavoPrometti\\Cert\\santander_cert.pem"  # ← Coloque o certificado .PEM aqui
    KEY_PEM_PATH = "C:\\Users\\GustavoPrometti\\Cert\\santander_key.pem"         # ← Chave privada .PEM (se separada)

    # ============================================================
    # AUTENTICAÇÃO
    # ============================================================
    
    try:
        # Inicializa o cliente de autenticação
        # Certificado e chave em arquivos separados
        santander = SantanderAuth(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            cert_path=CERT_PEM_PATH,
            key_path=KEY_PEM_PATH,
            ambiente="producao"
        )
        
        # Opção 2: Certificado e chave em arquivos separados
        # santander = SantanderAuth(
        #     client_id=CLIENT_ID,
        #     client_secret=CLIENT_SECRET,
        #     cert_path=CERT_PEM_PATH,
        #     key_path=KEY_PEM_PATH,
        #     ambiente="producao"
        # )
        
        print("\n" + "="*60)
        print("AUTENTICAÇÃO API SANTANDER")
        print("="*60)
        
        # Obter token de acesso
        print("\n⏳ Obtendo token de acesso...")
        token_data = santander.obter_token_acesso()
        
        print("\n✅ Token de acesso obtido com sucesso!")
        print(f"\nToken Type: {token_data['token_type']}")
        print(f"Expira em: {token_data['expires_at']}")
        print(f"Token salvo em: config/santander_token.json")
        
        # Verificar informações do token
        print("\n=== INFORMAÇÕES DO TOKEN ===")
        info = santander.get_token_info()
        for key, value in info.items():
            print(f"{key}: {value}")
        
        print("\n✅ Pronto para usar a API!")
        print("\nAgora você pode fazer requisições para a API do Santander")
        print("usando o token obtido.")
        
    except Exception as e:
        print(f"\n❌ Erro na autenticação: {e}")
        print("\nVerifique:")
        print("1. Client ID (X-Application-Key) está correto")
        print("2. Client Secret está correto")
        print("3. Certificado .PEM está no caminho correto")
        print("4. Certificado está válido e não expirou")
