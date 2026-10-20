import os
import json
import time
from datetime import datetime
from config import Config
from app.models import db
from sqlalchemy import text

class BackupService:
    def __init__(self):
        self.backup_dir = Config.BACKUP_DIR
        self.settings_file = Config.AUTO_BACKUP_SETTINGS_FILE
        os.makedirs(self.backup_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)

    def get_settings(self):
        default = {
            'enabled': False,
            'retention_count': 10,
            'last_backup': None,
            'last_status': 'Never run',
        }
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return {**default, **data}
            except Exception:
                pass
        return default

    def save_settings(self, settings):
        current = self.get_settings()
        new_settings = {
            'enabled': bool(settings.get('enabled', current['enabled'])),
            'retention_count': max(1, int(settings.get('retention_count', current['retention_count']))),
            'last_backup': settings.get('last_backup', current['last_backup']),
            'last_status': settings.get('last_status', current['last_status']),
        }
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(new_settings, f, indent=2)
        return True

    def list_backups(self):
        backups = []
        if not os.path.exists(self.backup_dir):
            return backups
        for f in os.listdir(self.backup_dir):
            if f.endswith('.sql'):
                fp = os.path.join(self.backup_dir, f)
                try:
                    stat = os.stat(fp)
                    backups.append({
                        'filename': f,
                        'size': stat.st_size,
                        'created_at': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                        'mtime': stat.st_mtime
                    })
                except Exception:
                    pass
        backups.sort(key=lambda x: x['mtime'], reverse=True)
        return backups

    def create_backup(self, force=False):
        settings = self.get_settings()
        if not settings['enabled'] and not force:
            return {'success': False, 'message': 'Auto backup is disabled.'}

        # Check 24-hour interval if not forced
        if not force and settings.get('last_backup'):
            try:
                last_time = datetime.strptime(settings['last_backup'], '%Y-%m-%d %H:%M:%S').timestamp()
                if time.time() - last_time < 86400:
                    return {
                        'success': False,
                        'message': f"Backup was already executed within the last 24 hours. Last backup: {settings['last_backup']}"
                    }
            except Exception:
                pass

        # Update last_backup timestamp to avoid concurrent race conditions
        settings['last_backup'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        settings['last_status'] = 'Running backup...'
        self.save_settings(settings)

        timestamp = int(time.time())
        now_str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename = f"backup_{now_str}_{timestamp}.sql"
        file_path = os.path.join(self.backup_dir, filename)

        try:
            sql_lines = [
                "-- Martech TMS Database Backup",
                f"-- Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "-- --------------------------------------------------------\n",
                "SET FOREIGN_KEY_CHECKS=0;\n"
            ]

            with db.engine.connect() as conn:
                # Get all table names
                tables_res = conn.execute(text("SHOW TABLES;"))
                tables = [r[0] for r in tables_res.fetchall()]

                for table in tables:
                    if table == 'ci_sessions':
                        continue

                    # Table structure
                    create_res = conn.execute(text(f"SHOW CREATE TABLE `{table}`;")).fetchone()
                    if create_res and len(create_res) > 1:
                        create_stmt = create_res[1]
                        sql_lines.append(f"DROP TABLE IF EXISTS `{table}`;")
                        sql_lines.append(f"{create_stmt};\n")

                    # Rows
                    rows_res = conn.execute(text(f"SELECT * FROM `{table}`;"))
                    rows = rows_res.fetchall()
                    if rows:
                        cols = [f"`{c}`" for c in rows_res.keys()]
                        cols_str = ", ".join(cols)
                        val_chunks = []
                        for row in rows:
                            escaped_vals = []
                            for v in row:
                                if v is None:
                                    escaped_vals.append("NULL")
                                elif isinstance(v, bool):
                                    escaped_vals.append("1" if v else "0")
                                elif isinstance(v, (int, float)):
                                    escaped_vals.append(str(v))
                                elif isinstance(v, (bytes, bytearray)):
                                    escaped_vals.append("0x" + bytes(v).hex())
                                else:
                                    # Escape string
                                    s = str(v).replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "\\r")
                                    escaped_vals.append(f"'{s}'")
                            val_chunks.append(f"({', '.join(escaped_vals)})")

                        # Group into batches bounded by both count and total byte size (~200KB)
                        batch = []
                        current_batch_size = 0
                        max_batch_bytes = 200 * 1024
                        max_batch_rows = 50

                        for chunk in val_chunks:
                            chunk_len = len(chunk)
                            if batch and (len(batch) >= max_batch_rows or (current_batch_size + chunk_len) > max_batch_bytes):
                                sql_lines.append(f"INSERT INTO `{table}` ({cols_str}) VALUES \n" + ",\n".join(batch) + ";\n")
                                batch = []
                                current_batch_size = 0
                            batch.append(chunk)
                            current_batch_size += chunk_len

                        if batch:
                            sql_lines.append(f"INSERT INTO `{table}` ({cols_str}) VALUES \n" + ",\n".join(batch) + ";\n")

            sql_lines.append("SET FOREIGN_KEY_CHECKS=1;\n")

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(sql_lines))

            pruned = self.prune_old_backups(settings['retention_count'])

            settings['last_backup'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            settings['last_status'] = f"Success: Backup '{filename}' created." + (f" Pruned {pruned} old file(s)." if pruned else "")
            self.save_settings(settings)

            return {
                'success': True,
                'message': f"Backup '{filename}' created successfully. " + (f"Pruned {pruned} old backups." if pruned else ""),
                'filename': filename
            }

        except Exception as e:
            settings['last_status'] = f"Failed: {str(e)}"
            self.save_settings(settings)
            return {'success': False, 'message': f"Backup failed: {str(e)}"}

    def prune_old_backups(self, retention_count):
        backups = self.list_backups()
        if len(backups) <= retention_count:
            return 0
        to_delete = backups[retention_count:]
        deleted = 0
        for b in to_delete:
            fp = os.path.join(self.backup_dir, b['filename'])
            if os.path.exists(fp):
                try:
                    os.remove(fp)
                    deleted += 1
                except Exception:
                    pass
        return deleted

    def delete_backup(self, filename):
        safe_name = os.path.basename(filename)
        fp = os.path.join(self.backup_dir, safe_name)
        if os.path.exists(fp):
            try:
                os.remove(fp)
                return True
            except Exception:
                return False
        return False

    @staticmethod
    def parse_sql_statements(content):
        """Robust multi-statement SQL splitter that respects strings, quotes, and escapes."""
        statements = []
        current = []
        in_quote = False
        quote_char = ''
        escaped = False

        lines = content.splitlines(keepends=True)
        for line in lines:
            # Skip pure comment lines when not inside a quoted literal
            if not in_quote:
                stripped = line.strip()
                if stripped.startswith('--') or stripped.startswith('#') or stripped.startswith('/*'):
                    continue

            for ch in line:
                if escaped:
                    current.append(ch)
                    escaped = False
                    continue

                if ch == '\\':
                    current.append(ch)
                    escaped = True
                    continue

                if ch in ("'", '"', '`'):
                    if in_quote:
                        if ch == quote_char:
                            in_quote = False
                            quote_char = ''
                    else:
                        in_quote = True
                        quote_char = ch

                current.append(ch)

                if ch == ';' and not in_quote:
                    stmt = ''.join(current).strip()
                    if stmt:
                        statements.append(stmt)
                    current = []

        rem = ''.join(current).strip()
        if rem:
            statements.append(rem)
        return statements

    def split_large_insert(self, stmt, max_bytes=250000):
        if len(stmt) <= max_bytes:
            return [stmt]
        upper = stmt.upper()
        v_idx = upper.find(' VALUES')
        if not (upper.startswith('INSERT INTO') and v_idx != -1):
            return [stmt]
        values_start = v_idx + 7
        while values_start < len(stmt) and stmt[values_start] in (' ', '\n', '\r', '\t'):
            values_start += 1
        prefix = stmt[:values_start]
        values_str = stmt[values_start:].strip().rstrip(';')

        rows = []
        in_str = False
        str_char = ''
        escape = False
        depth = 0
        row_start = 0

        for i, ch in enumerate(values_str):
            if escape:
                escape = False
                continue
            if ch == '\\':
                escape = True
                continue
            if in_str:
                if ch == str_char:
                    in_str = False
                continue
            else:
                if ch in ("'", '"'):
                    in_str = True
                    str_char = ch
                elif ch == '(':
                    if depth == 0:
                        row_start = i
                    depth += 1
                elif ch == ')':
                    depth -= 1
                    if depth == 0:
                        rows.append(values_str[row_start:i+1])

        if not rows:
            return [stmt]

        sub_statements = []
        current_batch = []
        current_size = len(prefix)
        for r in rows:
            r_len = len(r) + 2
            if current_batch and (current_size + r_len > max_bytes):
                sub_statements.append(f"{prefix}\n" + ",\n".join(current_batch) + ";")
                current_batch = []
                current_size = len(prefix)
            current_batch.append(r)
            current_size += r_len
        if current_batch:
            sub_statements.append(f"{prefix}\n" + ",\n".join(current_batch) + ";")
        return sub_statements

    def restore_backup(self, filename):
        safe_name = os.path.basename(filename)
        fp = os.path.join(self.backup_dir, safe_name)
        if not os.path.exists(fp):
            return {'success': False, 'message': 'Backup file not found.'}

        try:
            with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                sql_content = f.read()

            statements = self.parse_sql_statements(sql_content)

            # Close any open ORM session to release table locks
            try:
                db.session.remove()
            except Exception:
                pass

            raw_conn = db.engine.raw_connection()
            try:
                with raw_conn.cursor() as cur:
                    try:
                        cur.execute("SET SESSION wait_timeout = 600;")
                        cur.execute("SET SESSION net_read_timeout = 300;")
                        cur.execute("SET SESSION net_write_timeout = 300;")
                    except Exception:
                        pass

                    cur.execute("SET FOREIGN_KEY_CHECKS=0;")
                    for stmt in statements:
                        if len(stmt) > 300000 and stmt.upper().startswith("INSERT INTO"):
                            for chunk_stmt in self.split_large_insert(stmt, max_bytes=250000):
                                cur.execute(chunk_stmt)
                        else:
                            cur.execute(stmt)
                    cur.execute("SET FOREIGN_KEY_CHECKS=1;")
                raw_conn.commit()
            except Exception as e:
                raw_conn.rollback()
                raise e
            finally:
                raw_conn.close()

            return {'success': True, 'message': f"Database restored successfully from '{safe_name}'."}
        except Exception as e:
            return {'success': False, 'message': f"Restore failed: {str(e)}"}

    def check_and_run_auto_backup(self):
        settings = self.get_settings()
        if settings.get('enabled'):
            last_backup = settings.get('last_backup')
            if last_backup:
                try:
                    last_time = datetime.strptime(last_backup, '%Y-%m-%d %H:%M:%S').timestamp()
                    if time.time() - last_time < 86400:
                        return False
                except Exception:
                    pass
            res = self.create_backup(force=False)
            return res.get('success', False)
        return False
