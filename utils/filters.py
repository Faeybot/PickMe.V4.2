# Daftar kata kasar bisa kamu tambah sendiri di sini
BAD_WORDS = ["anjing", "bangsat", "tolol", "openbo", "slot", "gacor"]

def is_clean_text(text: str) -> bool:
    if not text:
        return True
    
    cleaned_text = text.lower()
    for word in BAD_WORDS:
        if word in cleaned_text:
            return False
    return True
