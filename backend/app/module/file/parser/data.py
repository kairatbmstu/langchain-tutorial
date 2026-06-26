import io
import json

from app.config import FILE_DATA_SAMPLE_ROWS


def parse_data_file(file_bytes: bytes, ext: str) -> str:
    ext = ext.lower().lstrip(".")
    try:
        import pandas as pd
        if ext == "csv":
            df = pd.read_csv(io.BytesIO(file_bytes))
        elif ext in ("xls", "xlsx"):
            df = pd.read_excel(io.BytesIO(file_bytes))
        elif ext == "json":
            data = json.loads(file_bytes.decode("utf-8", errors="replace"))
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                df = pd.json_normalize(data)
            else:
                return str(data)
        else:
            return ""

        buf = io.StringIO()
        df.info(buf=buf, memory_usage=False)
        schema = buf.getvalue()

        sample = df.head(FILE_DATA_SAMPLE_ROWS).to_string(index=False)

        cols = ", ".join(f"{col}: {dtype}" for col, dtype in df.dtypes.items())
        return (
            f"Columns: {cols}\n"
            f"Rows: {len(df)}\n"
            f"Schema:\n{schema}\n"
            f"Sample (first {FILE_DATA_SAMPLE_ROWS} rows):\n{sample}"
        )
    except ImportError:
        pass
    except Exception:
        pass

    try:
        return file_bytes.decode("utf-8", errors="replace")
    except Exception:
        return ""
