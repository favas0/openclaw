import re

STOPWORDS = {
    "new",
    "uk",
    "fast",
    "free",
    "delivery",
    "shipping",
    "sale",
    "best",
    "top",
    "quality",
    "offer",
    "with",
    "for",
    "and",
    "the",
    "a",
    "an",
    "to",
    "in",
    "of",
    "home",
    "remote",
    "control",
    "led",
    "display",
    "quiet",
    "portable",
}

BRAND_RISK_TERMS = {
    "nike",
    "adidas",
    "apple",
    "samsung",
    "sony",
    "dyson",
    "bosch",
    "lg",
    "philips",
    "panasonic",
    "xiaomi",
    "hp",
    "dell",
    "lenovo",
    "asus",
    "msi",
}

TOKEN_REPLACEMENTS = {
    "under desk": "underdesk",
    "standing desk": "standingdesk",
    "walking pad": "walkingpad",
    "office chair": "officechair",
    "sit stand": "sitstand",
    "2 in 1": "2in1",
    "l shaped": "lshaped",
}


def normalize_title(title: str) -> str:
    text = title.strip().lower()

    for old, new in TOKEN_REPLACEMENTS.items():
        text = text.replace(old, new)

    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def tokenize_title(title: str) -> list[str]:
    tokens = normalize_title(title).split()

    clean_tokens = []
    for token in tokens:
        if token in STOPWORDS:
            continue
        if len(token) <= 1:
            continue
        if token.isdigit():
            continue
        clean_tokens.append(token)

    return clean_tokens


def canonicalize_tokens(tokens: list[str]) -> list[str]:
    return sorted(set(tokens))


def canonical_title_from_tokens(tokens: list[str]) -> str:
    return " ".join(canonicalize_tokens(tokens))


def detect_brand_risk(title: str) -> bool:
    text = normalize_title(title)
    return any(term in text.split() for term in BRAND_RISK_TERMS)
