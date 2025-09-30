import streamlit as st
import wikipedia
import requests

# ==========================
# Language Options
# ==========================
LANGUAGES = {
    "English": {
        "code": "en",
        "wikipedia_lang": "en",
        "ui": {
            "title": "📚 Topic Summary with Book Recommendations",
            "search_history": "📝 Search History",
            "no_history": "No history...",
            "clear_all": "🗑️ Clear All History",
            "topic_input": "Topic or keyword:",
            "save_history": "Save to History",
            "search": "Search",
            "searching": "Searching...",
            "input_warning": "Input the topic/keyword first...",
            "topic_summary": "📖 Topic Summary (Wikipedia)",
            "book_recommendations": "📚 Book Recommendations",
            "no_books": "No books found.",
            "authors": "Authors",
            "year": "Year",
            "book_details": "Book Details",
            "save_success": "saved to history!",
            "already_saved": "is already in history.",
            "cannot_save": "Cannot save empty keyword!",
            "delete_hint": "Delete from history",
            "topic_not_found": "Topic not found for"
        }
    },
    "Indonesia": {
        "code": "id",
        "wikipedia_lang": "id",
        "ui": {
            "title": "📚 Ringkasan Topik dengan Rekomendasi Buku",
            "search_history": "📝 Riwayat Pencarian",
            "no_history": "Belum ada riwayat...",
            "clear_all": "🗑️ Hapus Semua Riwayat",
            "topic_input": "Topik atau kata kunci:",
            "save_history": "Simpan ke Riwayat",
            "search": "Cari",
            "searching": "Mencari...",
            "input_warning": "Masukkan topik/kata kunci terlebih dahulu...",
            "topic_summary": "📖 Ringkasan Topik (Wikipedia)",
            "book_recommendations": "📚 Rekomendasi Buku",
            "no_books": "Tidak ada buku yang ditemukan.",
            "authors": "Penulis",
            "year": "Tahun",
            "book_details": "Detail Buku",
            "save_success": "berhasil disimpan ke riwayat!",
            "already_saved": "sudah ada di riwayat.",
            "cannot_save": "Tidak dapat menyimpan kata kunci kosong!",
            "delete_hint": "Hapus dari riwayat",
            "topic_not_found": "Topik tidak ditemukan untuk"
        }
    }
}

# ==========================
# Function
# ==========================
def get_wikipedia_summary(query, sentences=5, lang="en"):
    try:
        # Set Wikipedia language
        wikipedia.set_lang(lang)
        
        # First try exact search without auto-suggestion
        try:
            summary = wikipedia.summary(query, sentences=sentences, auto_suggest=False, redirect=True)
            return summary
        except wikipedia.DisambiguationError as e:
            # If there are multiple options, use the first one
            summary = wikipedia.summary(e.options[0], sentences=sentences, auto_suggest=False, redirect=True)
            return f"**Note: Showing results for '{e.options[0]}' (multiple topics found for '{query}')**\n\n{summary}"
        except wikipedia.PageError:
            # If exact match fails, try with auto-suggestion as fallback
            try:
                suggested_title = wikipedia.suggest(query)
                if suggested_title and suggested_title.lower() != query.lower():
                    summary = wikipedia.summary(suggested_title, sentences=sentences, auto_suggest=False, redirect=True)
                    return f"**Note: No exact match found. Showing results for '{suggested_title}'**\n\n{summary}"
                else:
                    # Last resort: use auto_suggest=True
                    summary = wikipedia.summary(query, sentences=sentences, auto_suggest=True, redirect=True)
                    return summary
            except:
                raise
                
    except Exception as e:
        lang_config = LANGUAGES[st.session_state.selected_language]
        return f"{lang_config['ui']['topic_not_found']} '{query}'. Error: {e}"

def search_books(query, max_results=10, lang_code="en"):
    url = "https://www.googleapis.com/books/v1/volumes"
    # Adjust language restriction based on selected language
    lang_restrict = "id,en" if lang_code == "id" else "en,id"
    api_max_results = min(max_results * 2, 40)  # Request 2x lipat untuk filtering
    params = {"q": query, "maxResults": api_max_results, "langRestrict": lang_restrict}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
    except Exception:
        return []

    data = response.json()
    books = []

    if "items" in data:
        query_keywords = set(query.lower().split())
        
        for item in data["items"]:
            volume = item.get("volumeInfo", {})
            title = volume.get("title", "")
            description = volume.get("description", "")
            authors = volume.get("authors", [])
            categories = volume.get("categories", [])
            
            # Gabungkan semua teks untuk relevance check
            all_text = f"{title} {description} {' '.join(authors)} {' '.join(categories)}".lower()
            
            # Check relevance - minimal ada 1 keyword yang match
            is_relevant = any(keyword in all_text for keyword in query_keywords)
            
            # Atau check jika ada exact match atau substring match
            exact_match = query.lower() in all_text
            
            if is_relevant or exact_match:
                books.append({
                    "title": title if title else "No title",
                    "authors": ", ".join(authors) if authors else "Unknown",
                    "publishedDate": volume.get("publishedDate", "Unknown"),
                    "previewLink": volume.get("previewLink", "#"),
                    "relevance_score": len([kw for kw in query_keywords if kw in all_text])
                })
        
        # Sort berdasarkan relevance score (yang paling relevan di atas)
        books.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        # Limit hasil sesuai max_results tapi hanya yang relevan
        books = books[:max_results]
        
        # Remove relevance_score dari output final
        for book in books:
            book.pop("relevance_score", None)

    return books

# ==========================
# Initialize session state
# ==========================
if "history" not in st.session_state:
    st.session_state.history = []
if "current_keyword" not in st.session_state:
    st.session_state.current_keyword = ""
if "search_triggered" not in st.session_state:
    st.session_state.search_triggered = False
if "selected_language" not in st.session_state:
    st.session_state.selected_language = "English"

# Get current language configuration
lang_config = LANGUAGES[st.session_state.selected_language]
ui_text = lang_config["ui"]

# ==========================
# Custom CSS
# ==========================
st.markdown("""
    <style>
    .header-image { width:100%; height:200px; background-image: url('https://images.unsplash.com/photo-1512820790803-83ca734da794'); background-size:cover; background-position:center; border-radius:12px; margin-bottom:15px; }
    .title-text { text-align:center; font-size:32px; font-weight:bold; margin-bottom:20px; }
    .book-card { background:#2f2f2f; color:white; padding:15px 20px; border-radius:12px; box-shadow:0px 4px 10px rgba(0,0,0,0.3); margin-bottom:15px; }
    .history-item { display: flex; align-items: center; margin-bottom: 5px; }
    .history-button { flex: 1; margin-right: 5px; }
    .delete-button { width: 30px; }
    .language-selector { margin-bottom: 20px; }
    a { color:#4da6ff; }
    </style>
""", unsafe_allow_html=True)

# ==========================
# Header
# ==========================
st.markdown("<div class='header-image'></div>", unsafe_allow_html=True)
st.markdown(f"<div class='title-text'>{ui_text['title']}</div>", unsafe_allow_html=True)

# ==========================
# Sidebar: Language Selector & Search History
# ==========================
# Language Selector di sidebar
st.sidebar.markdown("### 🌐 Language / Bahasa")
selected_lang = st.sidebar.selectbox(
    "Select language:",
    options=list(LANGUAGES.keys()),
    index=list(LANGUAGES.keys()).index(st.session_state.selected_language),
    key="language_selector",
    label_visibility="collapsed"
)

# Update session state if language changed
if selected_lang != st.session_state.selected_language:
    st.session_state.selected_language = selected_lang
    st.rerun()

st.sidebar.markdown("---")  # Divider line

# Search History
st.sidebar.title(ui_text["search_history"])
if st.session_state.history:
    for idx, h in enumerate(st.session_state.history):
        col1, col2 = st.sidebar.columns([4, 1])
        
        with col1:
            if st.button(h, key=f"history_{idx}", use_container_width=True):
                st.session_state.current_keyword = h
                st.session_state.search_triggered = True
                st.rerun()
        
        with col2:
            if st.button("🗑️", key=f"delete_{idx}", help=ui_text["delete_hint"]):
                st.session_state.history.remove(h)
                st.rerun()
                
    # Clear all history button
    if st.sidebar.button(ui_text["clear_all"], type="secondary"):
        st.session_state.history = []
        st.rerun()
else:
    st.sidebar.info(ui_text["no_history"])

# ==========================
# Main Form
# ==========================
with st.form("search_form_unique"):
    keyword = st.text_input(ui_text["topic_input"], value=st.session_state.current_keyword, key="keyword_input")
    
    # Tombol search & save history - search jadi default untuk Enter key
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        submitted = st.form_submit_button(ui_text["search"])
    with col2:
        save_history = st.form_submit_button(ui_text["save_history"])
    # col3 kosong untuk spacing

# ==========================
# Logic untuk handle click dari history
# ==========================
if st.session_state.search_triggered:
    submitted = True
    keyword = st.session_state.current_keyword
    st.session_state.search_triggered = False

# ==========================
# Logic Search
# ==========================
if submitted:
    if keyword.strip() == "":
        st.warning(ui_text["input_warning"])
    else:
        # Simpan otomatis ke history saat search
        if keyword not in st.session_state.history:
            st.session_state.history.append(keyword)

        with st.spinner(ui_text["searching"]):
            summary = get_wikipedia_summary(keyword, sentences=20, lang=lang_config["wikipedia_lang"])
            books = search_books(keyword, max_results=10, lang_code=lang_config["code"])

        # Tampilkan ringkasan
        st.subheader(ui_text["topic_summary"])
        st.markdown(summary)

        # Tampilkan rekomendasi buku
        st.subheader(ui_text["book_recommendations"])
        if not books:
            st.info(ui_text["no_books"])
        else:
            for i, book in enumerate(books, start=1):
                st.markdown(f"""
                <div class="book-card">
                    <b>{i}. {book['title']}</b><br>
                    ✍️ {ui_text['authors']}: {book['authors']}<br>
                    📅 {ui_text['year']}: {book['publishedDate']}<br>
                    🔗 <a href="{book['previewLink']}" target="_blank">{ui_text['book_details']}</a>
                </div>
                """, unsafe_allow_html=True)

# ==========================
# Logic Save History Manual
# ==========================
if save_history:
    if keyword.strip() == "":
        st.warning(ui_text["cannot_save"])
    else:
        if keyword not in st.session_state.history:
            st.session_state.history.append(keyword)
            st.success(f"'{keyword}' {ui_text['save_success']}")
        else:
            st.info(f"'{keyword}' {ui_text['already_saved']}")