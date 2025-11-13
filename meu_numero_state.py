# meu_numero_state.py
from __future__ import annotations
import os, json, time, tempfile
from pathlib import Path

STATE_FILENAME = ".meu_numero_state.json"
LOCK_FILENAME  = ".meu_numero_state.lock"

class MeuNumeroState:
    def __init__(self, state_dir: str | Path):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.state_dir / STATE_FILENAME
        self.lock_path  = self.state_dir / LOCK_FILENAME

    # ---------- locking entre processos ----------
    def _acquire_lock(self, timeout_s: float = 5.0, poll_s: float = 0.05):
        start = time.time()
        while True:
            try:
                # criação exclusiva
                fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                return
            except FileExistsError:
                if time.time() - start > timeout_s:
                    raise TimeoutError("Não foi possível adquirir lock do meu_numero (timeout).")
                time.sleep(poll_s)

    def _release_lock(self):
        try:
            self.lock_path.unlink(missing_ok=True)
        except Exception:
            pass

    # ---------- leitura/gravação atômicas ----------
    def _read_state(self) -> dict:
        if not self.state_path.exists():
            return {}
        try:
            with self.state_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            # se corromper, renomeia e recomeça
            bak = self.state_path.with_suffix(self.state_path.suffix + ".bak")
            try: self.state_path.rename(bak)
            except Exception: pass
            return {}

    def _write_state_atomic(self, data: dict):
        tmp_fd, tmp_path = tempfile.mkstemp(prefix="mn_", suffix=".json", dir=str(self.state_dir))
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, self.state_path)  # atômico
        finally:
            try: os.remove(tmp_path)
            except FileNotFoundError: pass

    # ---------- API pública ----------
    def allocate_batch(self, dia_yyyymmdd: str, n: int) -> list[str]:
        """
        Retorna n 'meu_numero' únicos para o dia informado.
        Sequência global por dia: 1,2,3,... (10 dígitos zero-padded).
        """
        if n <= 0:
            return []
        self._acquire_lock()
        try:
            st = self._read_state()
            last = int(st.get(dia_yyyymmdd, 0))
            new_last = last + n
            if new_last > 9_999_999_999:
                raise OverflowError("Limite diário de 10 dígitos excedido.")
            st[dia_yyyymmdd] = new_last
            self._write_state_atomic(st)
            # gera a faixa (last+1 .. new_last)
            seq = [str(i).zfill(10) for i in range(last + 1, new_last + 1)]
            return seq
        finally:
            self._release_lock()

    def reset_today(self, dia_yyyymmdd: str):
        """Zera o contador do dia informado (para botão 'Limpar registros')."""
        self._acquire_lock()
        try:
            st = self._read_state()
            st[dia_yyyymmdd] = 0
            self._write_state_atomic(st)
        finally:
            self._release_lock()

    def clear_all(self):
        """Apaga todo o arquivo de estado (usa com cuidado)."""
        self._acquire_lock()
        try:
            self.state_path.unlink(missing_ok=True)
        finally:
            self._release_lock()
