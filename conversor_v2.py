# conversor_v2.py — V2C (GOORO) import-safe + execução por caminho
from __future__ import annotations
import re
import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

# =========================
# Transformação (GOORO)
# =========================
def transformar_gooro(conteudo: str) -> str:
    """
    Regras:
      - 0177410001 -> 0252977002
      - 52977002 -> 77410001, exceto quando vier precedido por '02'
        (ou seja, não troca '0252977002').
    """
    conteudo = conteudo.replace('0177410001', '0252977002')
    conteudo = re.sub(r'(?<!02)52977002', '77410001', conteudo)
    return conteudo

# =========================
# Núcleo de processamento
# =========================
def _gerar_nome_saida(caminho_venda: Path) -> Path:
    nome = caminho_venda.name
    if nome.endswith("_venda.txt"):
        return caminho_venda.with_name(nome.replace("_venda.txt", "_compra.txt"))
    return caminho_venda.with_name(f"{caminho_venda.stem}_compra.txt")

def _processar_arquivo(conteudo: str, caminho_venda: Path, arquivo_saida: str | None = None) -> Path:
    convertido = transformar_gooro(conteudo)
    if arquivo_saida:
        caminho_saida = Path(arquivo_saida)
    else:
        caminho_saida = _gerar_nome_saida(caminho_venda)

    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho_saida, "w", encoding="utf-8") as f:
        f.write(convertido)
    return caminho_saida

# =========================
# Entradas públicas (para o launcher)
# =========================
def executar_gooro_from_path(
    caminho_venda: str | os.PathLike | Path,
    arquivo_saida: str | None = None
) -> Path:
    """
    Executa o V2C (GOORO) usando um caminho já selecionado (launcher).
    Retorna o caminho do arquivo gerado.
    """
    caminho_venda = Path(caminho_venda)
    if not caminho_venda.exists() or not caminho_venda.is_file():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho_venda}")

    with open(caminho_venda, "r", encoding="utf-8") as f:
        conteudo = f.read()

    saida = _processar_arquivo(conteudo, caminho_venda, arquivo_saida)
    return saida

def executar_gooro(arquivo_saida: str | None = None) -> None:
    """
    Executa o V2C (GOORO) pedindo o arquivo via diálogo (uso manual).
    """
    path_str = filedialog.askopenfilename(
        title="Selecione o arquivo de venda (V2C)",
        filetypes=[("Arquivos de texto", "*.txt"), ("Todos", "*.*")]
    )
    if not path_str:
        return

    caminho_venda = Path(path_str)
    try:
        with open(caminho_venda, "r", encoding="utf-8") as f:
            conteudo = f.read()
        saida = _processar_arquivo(conteudo, caminho_venda, arquivo_saida)
        messagebox.showinfo("Conversão concluída", f"Arquivo de compra gerado:\n{saida}")
    except Exception as e:
        messagebox.showerror("Erro no Conversor V2C", str(e))

# =========================
# Modo standalone (opcional)
# =========================
def run_standalone():
    """
    Abre uma janela simples com APENAS o botão GOORO.
    Só é executado quando o arquivo é rodado diretamente.
    """
    root = tk.Tk()
    root.title("Conversor V2C – GOORO")

    # centraliza
    largura, altura = 520, 220
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    x = (sw // 2) - (largura // 2)
    y = (sh // 2) - (altura // 2)
    root.geometry(f"{largura}x{altura}+{x}+{y}")
    root.resizable(False, False)

    tk.Label(root, text="Conversor V2C (Venda → Compra) – GOORO",
             font=("Segoe UI", 14, "bold")).pack(pady=18)

    tk.Button(
        root,
        text="Selecionar arquivo de VENDA (.txt) e Converter (GOORO)",
        command=executar_gooro,
        width=46
    ).pack(pady=12)

    root.mainloop()

if __name__ == "__main__":
    run_standalone()
