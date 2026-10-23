import re

target = r"D:\Samvedna SIH with Truevoice\samvedna\samvedna\web\app\unit\page.tsx"

with open(target, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

# Replace corrupted k-anonymity symbol with clean mathematical notation
text = re.sub(r'span className="kpi-n num">k[^<]*{heat\.k}', 'span className="kpi-n num">k &ge; {heat.k}', text)
text = text.replace("â€\"", " — ")
text = text.replace("â€\x9d", " — ")
text = text.replace("â€”", " — ")
text = text.replace("â€¢", " • ")
text = text.replace("Â·", " • ")
text = text.replace("A·", " • ")
text = text.replace("â€", " — ")
text = text.replace("Â", " ")
text = text.replace("A\x9d", " ")
text = text.replace("A\xa0", " ")

# Clean up suppressed cells
text = text.replace('{cell.suppressed ? "?"', '{cell.suppressed ? "—"')
text = text.replace('{cell.suppressed ? "?"', '{cell.suppressed ? "—"')
text = text.replace('{cell.suppressed ? "—"', '{cell.suppressed ? "—"')

with open(target, "w", encoding="utf-8") as f:
    f.write(text)

print("Encoding successfully repaired!")
