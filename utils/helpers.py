import csv
import io

def standardize(self, text: str):
    rows = self.parse_pipe_csv(text)
    markdown_table = self.to_markdown_table(rows)
    
    return markdown_table

def parse_pipe_csv(text: str):
    rows = []
    reader = csv.reader(text.splitlines(), delimiter="|")
    for row in reader:
        rows.append([col.strip() for col in row])  # bersihin spasi
    return rows

def rows_to_csv_string(rows):
    """Convert list of lists jadi string CSV (pakai , atau | sesuai kebutuhan)"""
    output = io.StringIO()
    writer = csv.writer(output, delimiter=",", quoting=csv.QUOTE_MINIMAL)
    writer.writerows(rows)
    return output.getvalue()

def to_markdown_table(rows):
    if not rows:
        return ""

    # Header
    header = "| " + " | ".join(rows[0]) + " |"
    separator = "| " + " | ".join(["---"] * len(rows[0])) + " |"
    body = "\n".join("| " + " | ".join(row) + " |" for row in rows[1:])

    return "\n".join([header, separator, body])