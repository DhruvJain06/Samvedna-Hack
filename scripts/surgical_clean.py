target = r"D:\Samvedna SIH with Truevoice\samvedna\samvedna\web\app\unit\page.tsx"
with open(target, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

# Make legend horizontal
old_key = '<div className="heat-key" style={{ marginTop: 12 }}>'
new_key = '<div style={{ marginTop: 14, display: "flex", flexWrap: "wrap", alignItems: "center", gap: "16px", fontSize: "0.85rem" }}>'
text = text.replace(old_key, new_key)

# Fix min group text
text = text.replace("kâ%o¥{heat.k}", "k &ge; {heat.k}")
text = text.replace("k\ufffd%\ufffd{heat.k}", "k &ge; {heat.k}")
text = text.replace("k%{heat.k}", "k &ge; {heat.k}")

# Fix bullets and dashes in text
text = text.replace("â€¢", " • ")
text = text.replace("Â·", " • ")
text = text.replace("A·", " • ")
text = text.replace("â€\x9d", " — ")
text = text.replace("â€\u201d", " — ")
text = text.replace("â€”", " — ")
text = text.replace("A\xa0", " ")
text = text.replace("Â", " ")

# Clean up suppressed dash
text = text.replace('{cell.suppressed ? "?"', '{cell.suppressed ? "—"')
text = text.replace('{cell.suppressed ? "\ufffd\ufffd"', '{cell.suppressed ? "—"')

with open(target, "w", encoding="utf-8") as f:
    f.write(text)

print("Surgical update finished cleanly")
