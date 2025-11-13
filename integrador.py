# Launcher – CETIP (NC + Emissão Depósito + Operação Compra e Venda + Conversor V2C + CCI)
# Exige planilha/arquivo para cada processo marcado e (opcionalmente) grava os arquivos
# em uma pasta de saída escolhida. Se não escolher, salva ao lado da entrada.

from __future__ import annotations
import sys, threading, base64, os, webbrowser, importlib, importlib.util, traceback
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd  # ainda pode ser útil; não é usado na contagem final
import datetime as dt

APP_TITLE = "Launcher – CETIP"
APP_SUBTITLE = ("Selecione as planilhas/arquivos de entrada para cada processo marcado. "
                "Opcionalmente, escolha uma pasta de saída. Se não escolher, salvo ao lado das entradas.")

# ===== Ícone (PNG) embutido (opcional) =====
_APP_ICON_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAA..."  # encurtado

# ===== Tema opcional (ttkbootstrap) =====
USING_BOOTSTRAP = False
try:
    import ttkbootstrap as tb  # type: ignore
    USING_BOOTSTRAP = True
except Exception:
    USING_BOOTSTRAP = False

# ===== Util recursos / .exe =====
def resource_path(rel: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))  # PyInstaller
    p = Path(__file__).parent / rel
    return p if p.exists() else (base / rel)

# ===== Import seguro de módulos locais =====
def _import_local_module(mod_name: str):
    """
    Importa <mod_name>.py a partir da mesma pasta deste integrador.
    Se não existir, tenta import normal (instalado).
    """
    local_path = Path(__file__).parent / f"{mod_name}.py"
    if local_path.exists():
        spec = importlib.util.spec_from_file_location(mod_name, str(local_path))
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
            sys.modules[mod_name] = mod
            spec.loader.exec_module(mod)  # type: ignore[assignment]
            return mod
    return importlib.import_module(mod_name)

# ===== Helpers de saída =====
def _ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def _choose_out_dir_or_sibling(selected_path: Path, out_dir: str | None) -> Path:
    """
    Retorna a pasta onde salvar:
    - se out_dir estiver preenchido e existir (ou puder ser criada): usa out_dir
    - caso contrário: pasta da planilha/arquivo de entrada
    """
    if out_dir:
        out = Path(out_dir).expanduser()
        _ensure_dir(out)
        return out
    return selected_path.parent

def _stem_clean(p: Path) -> str:
    # nome base sem extensão, limpo para compor arquivos de saída
    return p.stem.replace(" ", "_")

# ===== Contagem REAL no arquivo gerado =====
def _count_registros_em_arquivo(path_arquivo: Path, tipo: str) -> int:
    """
    Conta quantos registros efetivamente foram gerados no arquivo:
      - tipo 'nc'   -> começa com 'NC   1'
      - tipo 'mda'  -> começa com 'MDA  1' (Depósito/Venda)
      - tipo 'cci'  -> começa com 'CCI  1' (atenção aos espaços do X(05))
    """
    if not path_arquivo or not path_arquivo.exists():
        return 0
    if tipo == "nc":
        prefixos = ["NC   1"]
    elif tipo == "mda":
        prefixos = ["MDA  1"]
    elif tipo == "cci":
        prefixos = ["CCI  1"]  # 'CCI' + dois espaços (X(05)) + '1'
    else:
        prefixos = []

    total = 0
    try:
        with open(path_arquivo, "r", encoding="utf-8", errors="ignore") as f:
            for ln in f:
                if any(ln.startswith(p) for p in prefixos):
                    total += 1
    except Exception:
        # Fallback extremamente conservador
        try:
            with open(path_arquivo, "r", errors="ignore") as f:
                for ln in f:
                    if any(ln.startswith(p) for p in prefixos):
                        total += 1
        except Exception:
            return 0
    return total

# ---------- Emissão NC ----------
def run_emissao_nc(logger_write, selected_path: Path | None, out_dir: str | None) -> int | None:
    if selected_path is None:
        messagebox.showwarning("Arquivo obrigatório", "Selecione a planilha de entrada para Emissão de NC.")
        return None

    logger_write("\n[NC] Iniciando Emissão de NC...\n")
    try:
        nc_mod = _import_local_module("EmissaoNC_v2")

        out_folder = _choose_out_dir_or_sibling(selected_path, out_dir)
        out_path = out_folder / f"NC_{_stem_clean(selected_path)}.txt"

        if hasattr(nc_mod, "main"):
            nc_mod.main(arquivo_saida=str(out_path),
                        caminho_entrada=str(selected_path),
                        sheet_index=1)  # 2ª aba
            logger_write(f"[NC] Saída: {out_path}\n")
        else:
            raise RuntimeError("O módulo de Emissão NC não possui main().")

        # >>> Contagem real no arquivo
        qtd_nc = _count_registros_em_arquivo(out_path, "nc")
        logger_write(f"[NC] Emissões geradas (arquivo): {qtd_nc}\n")
        logger_write("[NC] Finalizado com sucesso.\n")
        return qtd_nc
    except SystemExit:
        logger_write("[NC] Processo cancelado pelo usuário.\n")
        return None
    except Exception:
        err = traceback.format_exc()
        logger_write(f"[NC] ERRO:\n{err}\n")
        messagebox.showerror("Erro na Emissão de NC", err)
        return None

# ---------- Emissão Depósito (com papel do participante) ----------
def _rodar_dep_uma_vez(dep_mod, selected_path: Path, out_path: Path, papel: str, logger_write):
    papel = str(papel)
    if hasattr(dep_mod, "gerar_emissao_deposito_from_excel"):
        try:
            dep_mod.gerar_emissao_deposito_from_excel(
                caminho_planilha=selected_path,
                sheet_index=1,
                arquivo_saida=out_path,
                data_operacao=None,
                papel_participante=papel,
            )
        except TypeError:
            setattr(dep_mod, "PAPEL_PARTICIPANTE", papel)
            dep_mod.gerar_emissao_deposito_from_excel(
                caminho_planilha=selected_path,
                sheet_index=1,
                arquivo_saida=out_path,
                data_operacao=None,
            )
        except Exception as e1:
            logger_write(f"[DEP] Aviso: falhou sheet_index=1 ({e1.__class__.__name__}). Tentando aba 0…\n")
            try:
                dep_mod.gerar_emissao_deposito_from_excel(
                    caminho_planilha=selected_path,
                    sheet_index=0,
                    arquivo_saida=out_path,
                    data_operacao=None,
                    papel_participante=papel,
                )
            except TypeError:
                setattr(dep_mod, "PAPEL_PARTICIPANTE", papel)
                dep_mod.gerar_emissao_deposito_from_excel(
                    caminho_planilha=selected_path,
                    sheet_index=0,
                    arquivo_saida=out_path,
                    data_operacao=None,
                )
    elif hasattr(dep_mod, "gerar_emissao_deposito"):
        try:
            dep_mod.gerar_emissao_deposito(
                arquivo_saida=out_path,
                data_operacao=None,
                papel_participante=papel,
            )
        except TypeError:
            setattr(dep_mod, "PAPEL_PARTICIPANTE", papel)
            dep_mod.gerar_emissao_deposito(
                arquivo_saida=out_path,
                data_operacao=None,
            )
    elif hasattr(dep_mod, "main"):
        setattr(dep_mod, "PAPEL_PARTICIPANTE", papel)
        dep_mod.main()
    else:
        raise RuntimeError("Módulo emissao_deposito sem APIs conhecidas.")

def run_emissao_deposito(logger_write, selected_path: Path | None, papel_option: str, out_dir: str | None) -> int | None:
    if selected_path is None:
        messagebox.showwarning("Arquivo obrigatório", "Selecione a planilha de entrada para Emissão Depósito.")
        return None

    logger_write("\n[DEP] Iniciando Emissão Depósito...\n")
    try:
        dep_mod = _import_local_module("emissao_deposito")
        out_folder = _choose_out_dir_or_sibling(selected_path, out_dir)

        total_emitidas = 0

        def do_emissor():
            nonlocal total_emitidas
            out_path = out_folder / f"DEP_{_stem_clean(selected_path)}_EMISSOR.txt"
            _rodar_dep_uma_vez(dep_mod, selected_path, out_path, "02", logger_write)
            logger_write(f"[DEP] OK (Emissor). Saída: {out_path}\n")
            qtd = _count_registros_em_arquivo(out_path, "mda")
            logger_write(f"[DEP] Emissões (Emissor – arquivo): {qtd}\n")
            total_emitidas += qtd

        def do_distribuidor():
            nonlocal total_emitidas
            out_path = out_folder / f"DEP_{_stem_clean(selected_path)}_DISTRIBUIDOR.txt"
            _rodar_dep_uma_vez(dep_mod, selected_path, out_path, "03", logger_write)
            logger_write(f"[DEP] OK (Distribuidor). Saída: {out_path}\n")
            qtd = _count_registros_em_arquivo(out_path, "mda")
            logger_write(f"[DEP] Emissões (Distribuidor – arquivo): {qtd}\n")
            total_emitidas += qtd

        if papel_option == "ambos":
            do_emissor(); do_distribuidor()
        elif papel_option == "02":
            do_emissor()
        elif papel_option == "03":
            do_distribuidor()
        else:
            raise ValueError("Opção de papel inválida. Use '02', '03' ou 'ambos'.")

        logger_write(f"[DEP] Emissões geradas (TOTAL Depósito – arquivo): {total_emitidas}\n")
        logger_write("[DEP] Finalizado com sucesso.\n")
        return total_emitidas
    except Exception:
        err = traceback.format_exc()
        logger_write(f"[DEP] ERRO:\n{err}\n")
        messagebox.showerror("Erro na Emissão Depósito", err)
        return None

# ---------- Operação de Venda (header igual ao Depósito) ----------
def run_compra_venda(logger_write, selected_path: Path | None, out_dir: str | None) -> int | None:
    if selected_path is None:
        messagebox.showwarning("Arquivo obrigatório", "Selecione a planilha de entrada para Operação de Venda.")
        return None

    logger_write("\n[CV] Iniciando Operação de Venda…\n")
    try:
        mod_names = ["operacao_compra_venda", "Compra_Venda", "compra_venda"]
        last_err = None
        cv_mod = None
        for name in mod_names:
            try:
                cv_mod = _import_local_module(name)
                break
            except Exception as e:
                last_err = e
                continue
        if cv_mod is None:
            raise ModuleNotFoundError(f"Não foi possível importar: {mod_names}. Último erro: {last_err}")

        out_folder = _choose_out_dir_or_sibling(selected_path, out_dir)
        out_path = out_folder / f"Venda_{_stem_clean(selected_path)}.txt"

        if hasattr(cv_mod, "gerar_compra_venda_from_excel"):
            try:
                cv_mod.gerar_compra_venda_from_excel(
                    caminho_planilha=selected_path,
                    sheet_index=1,
                    arquivo_saida=out_path,
                    data_operacao=None,
                )
                logger_write(f"[CV] Saída: {out_path}\n")
            except TypeError:
                try:
                    cv_mod.gerar_compra_venda_from_excel(
                        caminho_planilha=selected_path,
                        sheet_index=1,
                        arquivo_saida=None,
                        data_operacao=None,
                    )
                    logger_write("[CV] O módulo não aceita 'arquivo_saida'; o arquivo foi salvo pelo módulo ao lado da entrada.\n")
                except Exception as e1:
                    logger_write(f"[CV] Aviso: falhou sheet_index=1 ({e1.__class__.__name__}). Tentando aba 0…\n")
                    try:
                        cv_mod.gerar_compra_venda_from_excel(
                            caminho_planilha=selected_path,
                            sheet_index=0,
                            arquivo_saida=None,
                            data_operacao=None,
                        )
                        logger_write("[CV] Rodou com sheet_index=0.\n")
                    except Exception:
                        raise
            except Exception as e:
                logger_write(f"[CV] Aviso: tentativa com arquivo_saida falhou ({e.__class__.__name__}). Tentando sem arquivo_saida…\n")
                try:
                    cv_mod.gerar_compra_venda_from_excel(
                        caminho_planilha=selected_path,
                        sheet_index=1,
                        arquivo_saida=None,
                        data_operacao=None,
                    )
                except Exception:
                    logger_write("[CV] Tentando sheet_index=0…\n")
                    cv_mod.gerar_compra_venda_from_excel(
                        caminho_planilha=selected_path,
                        sheet_index=0,
                        arquivo_saida=None,
                        data_operacao=None,
                    )
        elif hasattr(cv_mod, "main"):
            cv_mod.main()
            logger_write("[CV] Módulo executado via main(); destino de saída controlado pelo módulo.\n")
        else:
            raise RuntimeError("Módulo de Compra e Venda sem APIs conhecidas.")

        # >>> Contagem real no arquivo
        qtd_cv = _count_registros_em_arquivo(out_path, "mda")
        logger_write(f"[CV] Emissões geradas (arquivo): {qtd_cv}\n")
        logger_write("[CV] Finalizado com sucesso.\n")
        return qtd_cv
    except Exception:
        err = traceback.format_exc()
        logger_write(f"[CV] ERRO:\n{err}\n")
        messagebox.showerror("Erro na Operação de Venda", err)
        return None

# ---------- CCI ----------
def meu_numero_factory_from_state(out_dir: str | None, selected_path: Path):
    """
    Fábrica do 'meu número' SEM MeuNumeroState.
    Persiste em 'meu_numero_state.txt' na pasta de saída (ou ao lado da planilha).
    """
    state_dir = Path(out_dir) if out_dir else selected_path.parent
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / "meu_numero_state.txt"

    def _next() -> str:
        today = dt.date.today().isoformat()
        if state_file.exists():
            try:
                last_day, last_num = state_file.read_text(encoding="utf-8").strip().split(",")
                n = (int(last_num) + 1) if last_day == today else 1
            except Exception:
                n = 1
        else:
            n = 1
        state_file.write_text(f"{today},{n}", encoding="utf-8")
        return str(n).zfill(10)

    return _next

def run_cci(logger_write, selected_path: Path | None, operacao_option: str, modalidade_option: str, out_dir: str | None) -> int | None:
    if selected_path is None:
        messagebox.showwarning("Arquivo obrigatório", "Selecione a planilha de entrada para Emissão CCI.")
        return None

    logger_write("\n[CCI] Iniciando Emissão CCI…\n")
    try:
        cci_mod = _import_local_module("CCI")
        out_folder = _choose_out_dir_or_sibling(selected_path, out_dir)
        out_path = out_folder / f"CCI_{_stem_clean(selected_path)}.txt"

        # fábrica do Meu Número (agora interna, baseada em arquivo)
        fn_meu = meu_numero_factory_from_state(out_dir, selected_path)

        # gerar registros a partir do Excel
        if hasattr(cci_mod, "registros_from_excel") and hasattr(cci_mod, "gerar_arquivo_cci"):
            regs = cci_mod.registros_from_excel(
                path_xlsx=str(selected_path),
                operacao=operacao_option,       # 'VENDA' | 'COMPRA'
                modalidade=modalidade_option,   # 'Sem Modalidade' | 'Bruta'
                meu_numero_factory=fn_meu,
                sheet_index=0,                  # troque para 1 se sua planilha usar a 2ª aba
            )
            conteudo = cci_mod.gerar_arquivo_cci(regs, participante="LIMINETRUSTDTVM", data_arquivo=None)
            with open(out_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(conteudo + "\n" if not conteudo.endswith("\n") else conteudo)
            logger_write(f"[CCI] Saída: {out_path}\n")
        else:
            raise RuntimeError("Módulo CCI sem APIs esperadas (registros_from_excel/gerar_arquivo_cci).")

        # contagem real
        qtd_cci = _count_registros_em_arquivo(out_path, "cci")
        logger_write(f"[CCI] Registros gerados (arquivo): {qtd_cci}\n")
        logger_write("[CCI] Finalizado com sucesso.\n")
        return qtd_cci
    except Exception:
        err = traceback.format_exc()
        logger_write(f"[CCI] ERRO:\n{err}\n")
        messagebox.showerror("Erro na Emissão CCI", err)
        return None

# ---------- Conversor V2C (GOORO) ----------
def run_conversor_v2c(logger_write, selected_path: Path | None, out_dir: str | None):
    """
    Executa o Conversor V2C (GOORO) usando o arquivo .txt selecionado no launcher
    e grava o resultado diretamente na pasta de saída (se fornecida) ou ao lado da entrada).
    (Não participa da contagem de emissões.)
    """
    if selected_path is None:
        messagebox.showwarning("Arquivo obrigatório", "Selecione o arquivo de V2C (venda .txt).")
        return
    if selected_path.suffix.lower() != ".txt":
        if not messagebox.askyesno("Extensão diferente",
                                   "O arquivo não é .txt. Deseja continuar mesmo assim?"):
            return

    logger_write("\n[V2C] Iniciando Conversor V2C (GOORO)…\n")
    try:
        conv_mod = _import_local_module("conversor_v2")

        out_folder = _choose_out_dir_or_sibling(selected_path, out_dir)
        default_name = (
            (selected_path.name[:-10] + "_compra.txt") if selected_path.name.endswith("_venda.txt")
            else (selected_path.stem + "_compra.txt")
        )
        out_path = out_folder / default_name

        if hasattr(conv_mod, "executar_gooro_from_path"):
            saida = conv_mod.executar_gooro_from_path(
                caminho_venda=str(selected_path),
                arquivo_saida=str(out_path),
            )
            logger_write(f"[V2C] Saída: {saida}\n")
        elif hasattr(conv_mod, "executar_gooro"):
            try:
                conv_mod.executar_gooro(arquivo_saida=str(out_path))
                logger_write(f"[V2C] Saída: {out_path}\n")
            except TypeError:
                conv_mod.executar_gooro()
                logger_write("[V2C] O módulo não aceita 'arquivo_saida'; o arquivo foi salvo pelo módulo ao lado da entrada.\n")
        else:
            raise RuntimeError("Módulo conversor_v2 sem APIs conhecidas (esperado executar_gooro_from_path/ executar_gooro).")

        logger_write("[V2C] Finalizado com sucesso.\n")
    except Exception:
        err = traceback.format_exc()
        logger_write(f"[V2C] ERRO:\n{err}\n")
        messagebox.showerror("Erro no Conversor V2C", err)

# ---------- UI ----------
class UILogger:
    def __init__(self, text_widget: tk.Text):
        self.text = text_widget
    def write(self, msg: str):
        self.text.configure(state="normal")
        self.text.insert(tk.END, msg)
        self.text.see(tk.END)
        self.text.configure(state="disabled")

class LauncherCETIP:
    def __init__(self, root: tk.Tk | "tb.Window"):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1180x860")
        self._apply_icon()

        # Estados
        self.var_run_nc   = tk.BooleanVar(value=True)
        self.var_run_dep  = tk.BooleanVar(value=False)
        self.var_run_cv   = tk.BooleanVar(value=False)
        self.var_run_v2c  = tk.BooleanVar(value=False)
        self.var_run_cci  = tk.BooleanVar(value=False)
        self.var_in_nc    = tk.StringVar(value="")
        self.var_in_dep   = tk.StringVar(value="")
        self.var_in_cv    = tk.StringVar(value="")
        self.var_in_v2c   = tk.StringVar(value="")
        self.var_in_cci   = tk.StringVar(value="")
        self.var_out_dir  = tk.StringVar(value="")
        self.var_dep_papel = tk.StringVar(value="02")  # "02", "03" ou "ambos"

        # Opções CCI (do launcher)
        self.var_cci_operacao  = tk.StringVar(value="Venda")          # 'VENDA' | 'COMPRA'
        self.var_cci_modalidade= tk.StringVar(value="Sem Modalidade") # 'Sem Modalidade' | 'Bruta'

        # Contadores totais por tipo (para o resumo final)
        self._tot_nc = 0
        self._tot_dep = 0
        self._tot_cv = 0
        self._tot_cci = 0

        # Constrói UI
        self._build_ui()

        # Fallback: garante logger
        if not hasattr(self, "logger"):
            self.logger = UILogger(self.log_text)

    # ---- helpers ----
    def _apply_icon(self):
        try:
            data = base64.b64decode(_APP_ICON_PNG_B64)
            img = tk.PhotoImage(data=data)
            self.root.iconphoto(True, img)
            self._icon_img = img
        except Exception:
            pass

    def _open_folder(self, path: Path):
        try:
            if os.name == "nt":
                os.startfile(path if path.is_dir() else path.parent)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                os.system(f'open "{(path if path.is_dir() else path.parent).as_posix()}"')
            else:
                os.system(f'xdg-open "{(path if path.is_dir() else path.parent).as_posix()}"')
        except Exception:
            webbrowser.open((path if path.is_dir() else path.parent).as_uri())

    # ---- callbacks ----
    def _pick_in_nc(self):
        path = filedialog.askopenfilename(
            title="Selecione a planilha para Emissão de NC (2ª aba)",
            filetypes=[("Planilhas Excel", "*.xlsx;*.xlsm;*.xltx;*.xltm"), ("CSV", "*.csv"), ("Todos", "*.*")]
        )
        if path:
            self.var_in_nc.set(path)

    def _pick_in_dep(self):
        path = filedialog.askopenfilename(
            title="Selecione a planilha para Emissão Depósito (2ª aba)",
            filetypes=[("Planilhas Excel", "*.xlsx;*.xlsm;*.xltx;*.xltm"), ("CSV", "*.csv"), ("Todos", "*.*")]
        )
        if path:
            self.var_in_dep.set(path)

    def _pick_in_cv(self):
        path = filedialog.askopenfilename(
            title="Selecione a planilha para Operação  de Venda (2ª aba)",
            filetypes=[("Planilhas Excel", "*.xlsx;*.xlsm;*.xltx;*.xltm"), ("CSV", "*.csv"), ("Todos", "*.*")]
        )
        if path:
            self.var_in_cv.set(path)

    def _pick_in_v2c(self):
        path = filedialog.askopenfilename(
            title="Selecione o arquivo de V2C (venda .txt)",
            filetypes=[("Texto", "*.txt"), ("Todos", "*.*")]
        )
        if path:
            self.var_in_v2c.set(path)

    def _pick_in_cci(self):
        path = filedialog.askopenfilename(
            title="Selecione a planilha para Emissão CCI (aba principal)",
            filetypes=[("Planilhas Excel", "*.xlsx;*.xlsm;*.xltx;*.xltm"), ("CSV", "*.csv"), ("Todos", "*.*")]
        )
        if path:
            self.var_in_cci.set(path)

    def _pick_out_dir(self):
        folder = filedialog.askdirectory(title="Escolha a pasta de saída (opcional)")
        if folder:
            self.var_out_dir.set(folder)

    def _clear(self):
        self.var_in_nc.set("")
        self.var_in_dep.set("")
        self.var_in_cv.set("")
        self.var_in_v2c.set("")
        self.var_in_cci.set("")
        self.var_out_dir.set("")
        self.var_dep_papel.set("02")
        self.var_cci_operacao.set("VENDA")
        self.var_cci_modalidade.set("Sem Modalidade")
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        self.status_var.set("Aguardando…")
        self._tot_nc = self._tot_dep = self._tot_cv = self._tot_cci = 0

    def _run_threaded(self):
        threading.Thread(target=self._run_safe, daemon=True).start()

    def _run_safe(self):
        try:
            self._set_running(True)
            self.log_text.configure(state="normal")
            self.log_text.delete("1.0", "end")
            self.log_text.configure(state="disabled")

            if not any([self.var_run_nc.get(), self.var_run_dep.get(),
                        self.var_run_cv.get(), self.var_run_v2c.get(), self.var_run_cci.get()]):
                messagebox.showwarning("Atenção", "Selecione pelo menos um processo para executar.")
                return

            # Validar entradas
            selected_nc   = Path(self.var_in_nc.get()).expanduser()   if self.var_in_nc.get().strip()   else None
            selected_dep  = Path(self.var_in_dep.get()).expanduser()  if self.var_in_dep.get().strip()  else None
            selected_cv   = Path(self.var_in_cv.get()).expanduser()   if self.var_in_cv.get().strip()   else None
            selected_v2c  = Path(self.var_in_v2c.get()).expanduser()  if self.var_in_v2c.get().strip()  else None
            selected_cci  = Path(self.var_in_cci.get()).expanduser()  if self.var_in_cci.get().strip()  else None
            out_dir       = self.var_out_dir.get().strip() or None

            if self.var_run_nc.get() and selected_nc is None:
                messagebox.showwarning("Arquivo obrigatório", "Selecione a planilha para Emissão de NC."); return
            if self.var_run_dep.get() and selected_dep is None:
                messagebox.showwarning("Arquivo obrigatório", "Selecione a planilha para Emissão Depósito."); return
            if self.var_run_cv.get() and selected_cv is None:
                messagebox.showwarning("Arquivo obrigatório", "Selecione a planilha para Operação de Venda."); return
            if self.var_run_v2c.get() and selected_v2c is None:
                messagebox.showwarning("Arquivo obrigatório", "Selecione o arquivo de V2C (venda .txt)."); return
            if self.var_run_cci.get() and selected_cci is None:
                messagebox.showwarning("Arquivo obrigatório", "Selecione a planilha para Emissão CCI."); return

            if not hasattr(self, "logger"):
                self.logger = UILogger(self.log_text)

            # Zera totais
            self._tot_nc = self._tot_dep = self._tot_cv = self._tot_cci = 0

            # Executa na ordem marcada
            if self.var_run_nc.get():
                self.status_var.set("Rodando: Emissão de NC…")
                self.logger.write("> Rodando Emissão de NC\n")
                qtd_nc = run_emissao_nc(self.logger.write, selected_nc, out_dir)
                if isinstance(qtd_nc, int):
                    self._tot_nc += qtd_nc

            if self.var_run_dep.get():
                self.status_var.set("Rodando: Emissão Depósito…")
                self.logger.write("> Rodando Emissão Depósito\n")
                qtd_dep = run_emissao_deposito(self.logger.write, selected_dep, self.var_dep_papel.get(), out_dir)
                if isinstance(qtd_dep, int):
                    self._tot_dep += qtd_dep

            if self.var_run_cv.get():
                self.status_var.set("Rodando: Operação de Venda…")
                self.logger.write("> Rodando Operação de Venda (header)\n")
                qtd_cv = run_compra_venda(self.logger.write, selected_cv, out_dir)
                if isinstance(qtd_cv, int):
                    self._tot_cv += qtd_cv

            if self.var_run_cci.get():
                self.status_var.set("Rodando: Emissão CCI…")
                self.logger.write(f"> Rodando Emissão CCI (Operação: {self.var_cci_operacao.get()} | Modalidade: {self.var_cci_modalidade.get()})\n")
                qtd_cci = run_cci(self.logger.write, selected_cci, self.var_cci_operacao.get(), self.var_cci_modalidade.get(), out_dir)
                if isinstance(qtd_cci, int):
                    self._tot_cci += qtd_cci

            if self.var_run_v2c.get():
                self.status_var.set("Rodando: Conversor V2C…")
                self.logger.write("> Rodando Conversor V2C (GOORO)\n")
                run_conversor_v2c(self.logger.write, selected_v2c, out_dir)

            # ---- Resumo final ----
            self.logger.write("\n==== Resumo final das emissões ====\n")
            self.logger.write(f"NC: {self._tot_nc}\n")
            self.logger.write(f"Depósito: {self._tot_dep}\n")
            self.logger.write(f"Venda: {self._tot_cv}\n")
            self.logger.write(f"CCI: {self._tot_cci}\n")
            self.logger.write(f"Total (NC + Depósito + Venda + CCI): {self._tot_nc + self._tot_dep + self._tot_cv + self._tot_cci}\n")
            self.logger.write("===================================\n")

            self.status_var.set("Finalizado.")
            messagebox.showinfo("Processo finalizado", "CETIP – Processos concluídos.")

        except Exception as e:
            self.status_var.set("Erro.")
            messagebox.showerror("Erro", f"Ocorreu um erro:\n{e}")
        finally:
            self._set_running(False)

    def _set_running(self, running: bool):
        state = "disabled" if running else "normal"
        for w in self._toggle_when_running:
            try:
                w.configure(state=state)
            except Exception:
                pass
        if running:
            self.progress.start(10)
            self.status_var.set("Processando…")
        else:
            self.progress.stop()

    # ---- construção da UI (layout revisado) ----
    def _build_ui(self):
        root = self.root
        if USING_BOOTSTRAP:
            pass
        else:
            try:
                s = ttk.Style()
                s.theme_use("clam")
                s.configure("TLabelframe.Label", foreground="#333", font=("Segoe UI", 10, "bold"))
            except Exception:
                pass

        # grid base
        root.columnconfigure(0, weight=1)
        for r in (1, 3, 5, 7, 9):
            root.rowconfigure(r, weight=0)
        root.rowconfigure(9, weight=1)

        # ===== Menu (Sobre) =====
        menubar = tk.Menu(root)
        def _about():
            messagebox.showinfo("Sobre", "Launcher – CETIP\nKanastra – Utilitário de geração de arquivos.\nUI com ttk/ttkbootstrap.")
        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="Sobre", command=_about)
        menubar.add_cascade(label="Ajuda", menu=helpmenu)
        root.config(menu=menubar)

        # ===== Header =====
        frm_head = ttk.Frame(root, padding=(18, 14, 18, 8))
        frm_head.grid(row=0, column=0, sticky="ew")
        ttk.Label(frm_head, text=APP_TITLE, font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(frm_head, text=APP_SUBTITLE, foreground="#5a5a5a", padding=(0, 2, 0, 0), wraplength=980).pack(anchor="w")

        # ===== Linha principal (Processos + Entradas) =====
        frm_main = ttk.Frame(root, padding=(18, 8, 18, 8))
        frm_main.grid(row=1, column=0, sticky="ew")
        frm_main.columnconfigure(1, weight=1)

        # Processos
        box_left = ttk.Labelframe(frm_main, text="Processos", padding=(12, 8))
        box_left.grid(row=0, column=0, sticky="nsw", padx=(0, 16))
        chk_nc   = ttk.Checkbutton(box_left, text="Emissão NC", variable=self.var_run_nc)
        chk_dep  = ttk.Checkbutton(box_left, text="Emissão Depósito", variable=self.var_run_dep)
        chk_cv   = ttk.Checkbutton(box_left, text="Operação de Venda", variable=self.var_run_cv)
        chk_cci  = ttk.Checkbutton(box_left, text="Emissão CCI", variable=self.var_run_cci)
        chk_v2c  = ttk.Checkbutton(box_left, text="Conversor V2C", variable=self.var_run_v2c)
        chk_nc.grid(row=0, column=0, sticky="w", pady=4)
        chk_dep.grid(row=1, column=0, sticky="w", pady=4)
        chk_cv.grid(row=2, column=0, sticky="w", pady=4)
        chk_cci.grid(row=3, column=0, sticky="w", pady=4)
        chk_v2c.grid(row=4, column=0, sticky="w", pady=4)

        # Entradas
        box_inputs = ttk.Labelframe(frm_main, text="Entradas", padding=(12, 10))
        box_inputs.grid(row=0, column=1, sticky="nsew")
        box_inputs.columnconfigure(1, weight=1)

        ttk.Label(box_inputs, text="Entrada — Emissão NC:").grid(row=0, column=0, sticky="w", padx=(2, 8), pady=(0, 4))
        ent_nc = ttk.Entry(box_inputs, textvariable=self.var_in_nc)
        ent_nc.grid(row=0, column=1, sticky="ew", pady=(0, 4))
        btn_nc = ttk.Button(box_inputs, text="Escolher…", command=self._pick_in_nc)
        btn_nc.grid(row=0, column=2, padx=(8, 2), pady=(0, 4))

        ttk.Label(box_inputs, text="Entrada — Emissão Depósito:").grid(row=1, column=0, sticky="w", padx=(2, 8), pady=(6, 0))
        ent_dep = ttk.Entry(box_inputs, textvariable=self.var_in_dep)
        ent_dep.grid(row=1, column=1, sticky="ew", pady=(6, 0))
        btn_dep = ttk.Button(box_inputs, text="Escolher…", command=self._pick_in_dep)
        btn_dep.grid(row=1, column=2, padx=(8, 2), pady=(6, 0))

        ttk.Label(box_inputs, text="Entrada — Operação de Venda:").grid(row=2, column=0, sticky="w", padx=(2, 8), pady=(6, 0))
        ent_cv = ttk.Entry(box_inputs, textvariable=self.var_in_cv)
        ent_cv.grid(row=2, column=1, sticky="ew", pady=(6, 0))
        btn_cv = ttk.Button(box_inputs, text="Escolher…", command=self._pick_in_cv)
        btn_cv.grid(row=2, column=2, padx=(8, 2), pady=(6, 0))

        ttk.Label(box_inputs, text="Entrada — Emissão CCI:").grid(row=3, column=0, sticky="w", padx=(2, 8), pady=(6, 0))
        ent_cci = ttk.Entry(box_inputs, textvariable=self.var_in_cci)
        ent_cci.grid(row=3, column=1, sticky="ew", pady=(6, 0))
        btn_cci = ttk.Button(box_inputs, text="Escolher…", command=self._pick_in_cci)
        btn_cci.grid(row=3, column=2, padx=(8, 2), pady=(6, 0))

        ttk.Label(box_inputs, text="Entrada — V2C (venda .txt):").grid(row=4, column=0, sticky="w", padx=(2, 8), pady=(6, 0))
        ent_v2c = ttk.Entry(box_inputs, textvariable=self.var_in_v2c)
        ent_v2c.grid(row=4, column=1, sticky="ew", pady=(6, 0))
        btn_v2c = ttk.Button(box_inputs, text="Escolher…", command=self._pick_in_v2c)
        btn_v2c.grid(row=4, column=2, padx=(8, 2), pady=(6, 0))

        # ===== Pasta de saída (opcional) =====
        box_out = ttk.Labelframe(root, text="Pasta de saída (opcional)", padding=(12, 8))
        box_out.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 8))
        box_out.columnconfigure(0, weight=1)
        ent_out = ttk.Entry(box_out, textvariable=self.var_out_dir)
        ent_out.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(box_out, text="Escolher pasta…", command=self._pick_out_dir).grid(row=0, column=1, sticky="e")

        # ===== Papel do participante (somente Emissão Depósito) =====
        box_papel = ttk.Labelframe(
            root,
            text="Opções – Emissão Depósito (Papel do Participante)",
            padding=(12, 8),
        )
        box_papel.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 2))
        r1 = ttk.Radiobutton(box_papel, text="Emissor",      value="02",   variable=self.var_dep_papel)
        r2 = ttk.Radiobutton(box_papel, text="Distribuidor", value="03",   variable=self.var_dep_papel)
        r3 = ttk.Radiobutton(box_papel, text="Ambos",        value="ambos",variable=self.var_dep_papel)
        r1.grid(row=0, column=0, sticky="w", padx=(4, 16))
        r2.grid(row=0, column=1, sticky="w", padx=(0, 16))
        r3.grid(row=0, column=2, sticky="w")
        ttk.Label(
            box_papel,
            text="Se 'Ambos' for selecionado, dois arquivos serão gerados (emissor e distribuidor).",
            foreground="#6a6a6a",
        ).grid(row=1, column=0, columnspan=3, sticky="w", padx=(4, 0), pady=(6, 0))

        # ===== Opções do CCI =====
        box_cci = ttk.Labelframe(
            root,
            text="Opções – Emissão CCI",
            padding=(12, 10),
        )
        box_cci.grid(row=4, column=0, sticky="ew", padx=18, pady=(0, 8))

        # Operação
        ttk.Label(box_cci, text="Operação:").grid(row=0, column=0, sticky="w")
        r_ven = ttk.Radiobutton(box_cci, text="Venda ", value="Venda", variable=self.var_cci_operacao)
        r_com = ttk.Radiobutton(box_cci, text="Compra", value="Compra", variable=self.var_cci_operacao)
        r_ven.grid(row=0, column=1, sticky="w", padx=(8, 16))
        r_com.grid(row=0, column=2, sticky="w")

        # Modalidade
        ttk.Label(box_cci, text="Modalidade:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        r_sem = ttk.Radiobutton(box_cci, text="Sem Modalidade", value="Sem Modalidade", variable=self.var_cci_modalidade)
        r_bru = ttk.Radiobutton(box_cci, text="Bruta", value="Bruta", variable=self.var_cci_modalidade)
        r_sem.grid(row=1, column=1, sticky="w", padx=(8, 16), pady=(6, 0))
        r_bru.grid(row=1, column=2, sticky="w", pady=(6, 0))

        # ===== Ações =====
        frm_actions = ttk.Frame(root, padding=(18, 6, 18, 4))
        frm_actions.grid(row=5, column=0, sticky="ew")
        frm_actions.columnconfigure(0, weight=1)
        self.progress = ttk.Progressbar(frm_actions, mode="indeterminate")
        self.progress.grid(row=0, column=0, sticky="ew", padx=(0, 10), ipady=2)

        btn_clear = ttk.Button(frm_actions, text="Limpar", command=self._clear)
        btn_clear.grid(row=0, column=1, sticky="e", padx=(0, 8))

        btn_exec = ttk.Button(frm_actions, text="Executar", command=self._run_threaded)
        btn_exec.grid(row=0, column=2, sticky="e")

        # ===== Status =====
        self.status_var = tk.StringVar(value="Aguardando…")
        status_bar = ttk.Frame(root, padding=(18, 0))
        status_bar.grid(row=6, column=0, sticky="ew")
        status_bar.columnconfigure(0, weight=1)
        ttk.Label(status_bar, textvariable=self.status_var, foreground="#555", padding=(0, 2)).grid(row=0, column=0, sticky="w")

        # ===== Relatório =====
        frm_log = ttk.Labelframe(root, text="Relatório", padding=(10, 8))
        frm_log.grid(row=9, column=0, sticky="nsew", padx=18, pady=(4, 12))
        frm_log.rowconfigure(0, weight=1)
        frm_log.columnconfigure(0, weight=1)

        self.log_text = tk.Text(frm_log, height=12, wrap="word", font=("Segoe UI", 9))
        self.log_text.grid(row=0, column=0, sticky="nsew")

        scr = ttk.Scrollbar(frm_log, command=self.log_text.yview)
        scr.grid(row=0, column=1, sticky="ns")

        self.log_text.configure(yscrollcommand=scr.set, state="disabled")

        # Logger e widgets bloqueados durante execução
        self.logger = UILogger(self.log_text)
        self._toggle_when_running = [
            box_inputs, box_left, box_out, box_papel, box_cci,
            btn_exec, btn_clear, self.progress,
        ]

    # ---- estado de execução ----
    def _set_running(self, running: bool):
        state = "disabled" if running else "normal"
        for w in self._toggle_when_running:
            try:
                w.configure(state=state)
            except Exception:
                pass
        if running:
            self.progress.start(10)
            self.status_var.set("Processando…")
        else:
            self.progress.stop()

# ===== Entry point =====
def main():
    if USING_BOOTSTRAP:
        root = tb.Window(themename="flatly")
    else:
        root = tk.Tk()

    app = LauncherCETIP(root)

    # Centraliza janela
    root.update_idletasks()
    w, h = root.winfo_width(), root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (w // 2)
    y = (root.winfo_screenheight() // 2) - (h // 2)
    root.geometry(f"{w}x{h}+{x}+{y}")
    root.mainloop()

if __name__ == "__main__":
    main()
