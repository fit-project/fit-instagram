# fit-instagram

Instagram scraping module for the **FIT Project**, built using [PySide6](https://doc.qt.io/qtforpython/) and [Instaloader](https://instaloader.github.io/).  
Provides a graphical interface and structured workflow to acquire and preserve Instagram profile data, posts, and stories for forensic purposes, fully integrated into the FIT modular ecosystem.

---

## ⚠️ Project Status

**fit-instagram is temporarily suspended.**  
This module is entirely based on [Instaloader](https://instaloader.github.io/), which interacts with Instagram’s private GraphQL endpoints.  
Due to the latest changes in Instagram’s internal API and rate-limiting policies, Instaloader is now frequently affected by:

- `HTTP 429 – Too Many Requests` (IP-based throttling)  
- `HTTP 401 – Unauthorized` (login and session restrictions)

As a result, automated or large-scale acquisition of posts, stories, and related media has become unreliable.  
The module currently supports **only limited public information** such as profile metadata and profile pictures.

fit-instagram will remain paused until:
- Instaloader or a similar library restores stable API access, **or**
- a new, legally compliant method of forensic acquisition becomes available.

---

## 🔗 Related FIT components

This package is designed to work alongside other FIT modules:

- [`fit-scraper`](https://github.com/fit-project/fit-scraper) – Base utilities and orchestration for acquisition

---

## 🐍 Dependencies

Main dependencies:

- Python `>=3.11,<3.14`
- [PySide6](https://pypi.org/project/PySide6/)
- [Instaloader](https://pypi.org/project/instaloader/)

See `pyproject.toml` for the full list and version constraints.

---

## 📦 Installation

Install with [Poetry](https://python-poetry.org/):

```bash
poetry install
```

---

## 🧩 Notes

- Only public profile information (e.g., username, biography, follower count, and profile picture) may currently be retrievable.  
- Attempts to acquire posts, stories, highlights, or saved content will often trigger `HTTP 401` or `HTTP 429` responses.  
- The current release (`3.0.0-beta.1`) represents a **major architectural migration** to the new FIT modular structure and **PySide6 framework**, keeping Instaloader as the underlying acquisition engine.

---

## Contributing

Until further notice, contributions related to scraping logic or bypass mechanisms are discouraged,  
as they would be immediately invalidated by future Instagram API changes.

Contributions focused on architecture, UI consistency, or forensic packaging remain welcome.

1. Fork this repository.  
2. Create a new branch (`git checkout -b feat/my-feature`).  
3. Commit your changes using [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).  
4. Submit a Pull Request describing your modification.

---

**Version:** `3.0.0-beta.1`  
**Status:** Temporarily suspended due to API restrictions affecting Instaloader  
**License:** GPL-3.0-only  
