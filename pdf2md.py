import pymupdf4llm
md_text = pymupdf4llm.to_markdown("/home/naoto/open-web-ui/JCS2025_Iwamoto.pdf", write_images=True)
with open("output.md", "w", encoding="utf-8") as f:
    f.write(md_text)
