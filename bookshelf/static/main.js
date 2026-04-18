const appState = {
    genres: [],
    books: [],
    dashboardFilters: {
        q: "",
        status: "",
        genreId: ""
    },
    modal: {
        mode: "create",
        bookId: null,
        rating: null
    },
    detail: {
        book: null,
        selectedConnectionBook: null,
        connectionResults: [],
        searchTimer: null
    }
}

document.addEventListener("DOMContentLoaded", init)

function init() {
    initializeGlobalUi()
    initializeBookModal()
    renderStarInput()

    if (document.getElementById("books-grid")) {
        initializeDashboardPage()
    }

    if (document.getElementById("page-detail")) {
        initializeDetailPage()
    }
}

function initializeGlobalUi() {
    document.getElementById("btn-add-book")?.addEventListener("click", async event => {
        event.preventDefault()
        await openBookModal("create")
    })

    document.getElementById("btn-modal-close")?.addEventListener("click", closeBookModal)
    document.getElementById("btn-modal-cancel")?.addEventListener("click", closeBookModal)
    document.getElementById("btn-modal-save")?.addEventListener("click", saveBook)

    document.querySelectorAll(".modal-backdrop").forEach(backdrop => {
        backdrop.addEventListener("click", event => {
            const modal = event.target.closest(".modal")
            if (!modal) return
            modal.classList.add("hidden")
            modal.setAttribute("aria-hidden", "true")
        })
    })

    document.addEventListener("keydown", event => {
        if (event.key === "Escape") {
            closeBookModal()
            closeConnectionModal()
        }
    })
}

async function initializeDashboardPage() {
    const searchInput = document.getElementById("search-input")
    const genreSelect = document.getElementById("filter-genre-select")

    let searchTimer = null

    searchInput?.addEventListener("input", event => {
        window.clearTimeout(searchTimer)
        searchTimer = window.setTimeout(() => {
            appState.dashboardFilters.q = event.target.value.trim()
            loadDashboardBooks()
        }, 180)
    })

    document.querySelectorAll(".pill").forEach(button => {
        button.addEventListener("click", () => {
            document.querySelectorAll(".pill").forEach(item => item.classList.remove("active"))
            button.classList.add("active")
            appState.dashboardFilters.status = button.dataset.status || ""
            loadDashboardBooks()
        })
    })

    genreSelect?.addEventListener("change", event => {
        appState.dashboardFilters.genreId = event.target.value
        loadDashboardBooks()
    })

    document.getElementById("btn-empty-add")?.addEventListener("click", async () => {
        await openBookModal("create")
    })

    await Promise.all([
        loadGenres(),
        loadDashboardStats()
    ])

    renderGenreFilterOptions()
    await loadDashboardBooks()
}

function initializeDetailPage() {
    const bookId = Number(document.getElementById("page-detail")?.dataset.bookId)

    document.getElementById("btn-edit")?.addEventListener("click", async () => {
        if (!appState.detail.book) return
        await openBookModal("edit", appState.detail.book.id)
    })

    document.getElementById("btn-delete")?.addEventListener("click", deleteCurrentBook)
    document.getElementById("btn-add-connection")?.addEventListener("click", openConnectionModal)
    document.getElementById("conn-search")?.addEventListener("input", handleConnectionSearch)

    if (bookId) {
        loadBookDetail(bookId)
    }
}

async function apiRequest(path, options = {}) {
    const response = await fetch(path, {
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {})
        },
        ...options
    })

    const payload = await response.json().catch(() => ({
        data: null,
        error: "Resposta invalida da API"
    }))

    if (!response.ok || payload.error) {
        throw new Error(payload.error || "Falha na requisicao")
    }

    return payload.data
}

async function loadGenres() {
    if (appState.genres.length) {
        renderGenreCheckboxes()
        return appState.genres
    }

    appState.genres = await apiRequest("/api/genres")
    renderGenreCheckboxes()
    return appState.genres
}

async function loadDashboardStats() {
    try {
        const stats = await apiRequest("/api/stats")
        document.getElementById("stat-total").textContent = stats.total ?? "—"
        document.getElementById("stat-read").textContent = stats.by_status?.read ?? "—"
        document.getElementById("stat-rating").textContent = stats.avg_rating ?? "—"
        document.getElementById("stat-connections").textContent = stats.total_connections ?? "—"
    } catch (error) {
        showToast(error.message, "error")
    }
}

async function loadDashboardBooks() {
    const grid = document.getElementById("books-grid")
    const emptyState = document.getElementById("empty-state")

    if (!grid || !emptyState) return

    const params = new URLSearchParams()
    if (appState.dashboardFilters.q) params.set("q", appState.dashboardFilters.q)
    if (appState.dashboardFilters.status) params.set("status", appState.dashboardFilters.status)
    if (appState.dashboardFilters.genreId) params.set("genre_id", appState.dashboardFilters.genreId)
    params.set("sort", "created_at")
    params.set("order", "desc")

    try {
        const books = await apiRequest(`/api/books?${params.toString()}`)
        appState.books = books
        grid.innerHTML = books.map(renderBookCard).join("")
        emptyState.classList.toggle("hidden", books.length > 0)
    } catch (error) {
        grid.innerHTML = ""
        emptyState.classList.add("hidden")
        showToast(error.message, "error")
    }
}

function renderGenreFilterOptions() {
    const genreSelect = document.getElementById("filter-genre-select")
    if (!genreSelect) return

    genreSelect.innerHTML = `
        <option value="">todos os gêneros</option>
        ${appState.genres.map(genre => `<option value="${genre.id}">${escapeHtml(genre.name)}</option>`).join("")}
    `
}

function renderGenreCheckboxes(selectedIds = []) {
    const container = document.getElementById("genre-checkboxes")
    if (!container) return

    container.innerHTML = appState.genres.map(genre => `
        <label class="checkbox-chip">
            <input type="checkbox" value="${genre.id}" ${selectedIds.includes(genre.id) ? "checked" : ""}>
            <span><i class="swatch" style="background:${genre.color_hex}"></i>${escapeHtml(genre.name)}</span>
        </label>
    `).join("")
}

function renderBookCard(book) {
    const stars = "★".repeat(Math.round(book.rating || 0)) + "☆".repeat(5 - Math.round(book.rating || 0))
    const statusLabel = {
        want: "quero ler",
        reading: "lendo",
        read: "lido"
    }[book.status]

    const primaryGenre = book.genres?.[0]
    const genrePill = primaryGenre
        ? `<span class="genre-pill" style="background:${primaryGenre.color_hex}22;color:${primaryGenre.color_hex}">${escapeHtml(primaryGenre.name)}</span>`
        : ""

    const coverStyle = book.cover_url
        ? `background-image:url('${escapeHtml(book.cover_url)}')`
        : `background:${primaryGenre?.color_hex || "#888780"}22`

    return `
        <article class="book-card" data-id="${book.id}" onclick="location.href='/books/${book.id}'">
            <div class="book-cover" style="${coverStyle}">
                ${!book.cover_url ? `<span class="cover-initials">${escapeHtml(book.title.slice(0, 2).toUpperCase())}</span>` : ""}
            </div>
            <div class="book-info">
                <div class="book-title">${escapeHtml(book.title)}</div>
                <div class="book-author">${escapeHtml(book.author)}</div>
                ${book.rating ? `<div class="book-stars">${stars}</div>` : ""}
                <div class="book-meta">
                    <span class="status-badge status-${book.status}">${statusLabel}</span>
                    ${genrePill}
                </div>
            </div>
        </article>
    `
}

function initializeBookModal() {
    const modal = document.getElementById("modal-book")
    if (!modal) return

    modal.querySelectorAll("input, textarea, select").forEach(element => {
        element.addEventListener("keydown", event => {
            if (event.key === "Enter" && element.tagName !== "TEXTAREA") {
                event.preventDefault()
                saveBook()
            }
        })
    })
}

function renderStarInput() {
    const container = document.getElementById("star-input")
    if (!container) return

    const starButtons = Array.from({ length: 5 }, (_, index) => {
        const value = index + 1
        const active = appState.modal.rating >= value
        return `<button class="star-button ${active ? "active" : ""}" type="button" data-rating="${value}" aria-label="${value} estrelas">★</button>`
    })

    container.innerHTML = `
        ${starButtons.join("")}
        <button class="star-clear" type="button">limpar</button>
    `

    container.querySelectorAll(".star-button").forEach(button => {
        button.addEventListener("click", () => {
            appState.modal.rating = Number(button.dataset.rating)
            renderStarInput()
        })
    })

    container.querySelector(".star-clear")?.addEventListener("click", () => {
        appState.modal.rating = null
        renderStarInput()
    })
}

async function openBookModal(mode, bookId = null) {
    appState.modal.mode = mode
    appState.modal.bookId = bookId
    appState.modal.rating = null

    await loadGenres()

    const modal = document.getElementById("modal-book")
    const title = document.getElementById("modal-title")

    resetBookForm()

    if (mode === "edit" && bookId) {
        const book = await apiRequest(`/api/books/${bookId}`)
        fillBookForm(book)
        title.textContent = "Editar livro"
    } else {
        title.textContent = "Adicionar livro"
    }

    modal.classList.remove("hidden")
    modal.setAttribute("aria-hidden", "false")
}

function closeBookModal() {
    const modal = document.getElementById("modal-book")
    if (!modal) return
    modal.classList.add("hidden")
    modal.setAttribute("aria-hidden", "true")
}

function resetBookForm() {
    document.getElementById("book-title").value = ""
    document.getElementById("book-author").value = ""
    document.getElementById("book-year").value = ""
    document.getElementById("book-isbn").value = ""
    document.getElementById("book-cover").value = ""
    document.getElementById("book-status").value = "want"
    document.getElementById("book-tags").value = ""
    document.getElementById("book-review").value = ""
    appState.modal.rating = null
    renderStarInput()
    renderGenreCheckboxes([])
}

function fillBookForm(book) {
    document.getElementById("book-title").value = book.title || ""
    document.getElementById("book-author").value = book.author || ""
    document.getElementById("book-year").value = book.year || ""
    document.getElementById("book-isbn").value = book.isbn || ""
    document.getElementById("book-cover").value = book.cover_url || ""
    document.getElementById("book-status").value = book.status || "want"
    document.getElementById("book-tags").value = (book.tags || []).join(", ")
    document.getElementById("book-review").value = book.review || ""
    appState.modal.rating = book.rating || null
    renderStarInput()
    renderGenreCheckboxes((book.genres || []).map(genre => genre.id))
}

function collectBookPayload() {
    const selectedGenreIds = Array.from(document.querySelectorAll("#genre-checkboxes input:checked")).map(input => Number(input.value))
    const tags = document.getElementById("book-tags").value
        .split(",")
        .map(tag => tag.trim())
        .filter(Boolean)

    return {
        title: document.getElementById("book-title").value.trim(),
        author: document.getElementById("book-author").value.trim(),
        year: document.getElementById("book-year").value.trim() || null,
        isbn: document.getElementById("book-isbn").value.trim() || null,
        cover_url: document.getElementById("book-cover").value.trim() || null,
        status: document.getElementById("book-status").value,
        rating: appState.modal.rating,
        genre_ids: selectedGenreIds,
        tags,
        review: document.getElementById("book-review").value.trim() || null
    }
}

async function saveBook() {
    const payload = collectBookPayload()
    const isEditing = appState.modal.mode === "edit" && appState.modal.bookId
    const path = isEditing ? `/api/books/${appState.modal.bookId}` : "/api/books"
    const method = isEditing ? "PUT" : "POST"

    try {
        const savedBook = await apiRequest(path, {
            method,
            body: JSON.stringify(payload)
        })

        closeBookModal()
        showToast(isEditing ? "Livro atualizado." : "Livro criado.")

        if (document.getElementById("books-grid")) {
            await Promise.all([loadDashboardBooks(), loadDashboardStats()])
        }

        if (document.getElementById("page-detail")) {
            if (isEditing) {
                await loadBookDetail(savedBook.id)
            } else {
                location.href = `/books/${savedBook.id}`
            }
        }
    } catch (error) {
        showToast(error.message, "error")
    }
}

async function loadBookDetail(bookId) {
    try {
        const book = await apiRequest(`/api/books/${bookId}`)
        appState.detail.book = book
        renderBookDetail(book)
        loadBookContext(book.id)
    } catch (error) {
        showToast(error.message, "error")
        document.getElementById("page-detail").innerHTML = `<div class="empty-state">${escapeHtml(error.message)}</div>`
    }
}

function renderBookDetail(book) {
    const primaryGenre = book.genres?.[0]
    const cover = document.getElementById("detail-cover")
    const stars = "★".repeat(Math.round(book.rating || 0)) + "☆".repeat(5 - Math.round(book.rating || 0))

    cover.style.backgroundImage = book.cover_url ? `url('${book.cover_url}')` : "none"
    cover.style.backgroundColor = book.cover_url ? "transparent" : `${primaryGenre?.color_hex || "#888780"}22`
    cover.innerHTML = book.cover_url ? "" : `<span class="detail-cover-initials">${escapeHtml(book.title.slice(0, 2).toUpperCase())}</span>`

    document.getElementById("detail-title").textContent = book.title
    document.getElementById("detail-author").textContent = `${book.author}${book.year ? ` · ${book.year}` : ""}`
    document.getElementById("detail-stars").textContent = book.rating ? stars : "sem avaliação ainda"
    document.getElementById("status-select").value = book.status
    document.getElementById("detail-meta-line").textContent = book.isbn ? `ISBN ${book.isbn}` : "sem ISBN cadastrado"
    document.getElementById("detail-genres").innerHTML = (book.genres || []).map(genre => `
        <span class="genre-pill" style="background:${genre.color_hex}22;color:${genre.color_hex}">${escapeHtml(genre.name)}</span>
    `).join("")
    document.getElementById("detail-tags").innerHTML = (book.tags || []).map(tag => `
        <span class="tag-pill">${escapeHtml(tag)}</span>
    `).join("")

    const review = document.getElementById("detail-review")
    if (book.review) {
        review.textContent = book.review
        review.classList.remove("hidden")
    } else {
        review.classList.add("hidden")
    }

    renderConnections(book.connections || [])
}

function renderConnections(connections) {
    const list = document.getElementById("connections-list")
    const empty = document.getElementById("connections-empty")
    if (!list || !empty) return

    if (!connections.length) {
        list.innerHTML = ""
        empty.classList.remove("hidden")
        return
    }

    empty.classList.add("hidden")
    list.innerHTML = connections.map(connection => `
        <article class="connection-card">
            <div class="connection-main">
                <a class="connection-title" href="/books/${connection.book.id}">${escapeHtml(connection.book.title)}</a>
                <div class="conn-type-badge conn-type-${connection.type}">${connection.type}</div>
                ${connection.note ? `<div class="connection-note">${escapeHtml(connection.note)}</div>` : `<div class="connection-note">Sem nota adicional.</div>`}
            </div>
            <div class="connection-actions">
                <a class="btn-secondary" href="/books/${connection.book.id}">abrir</a>
                ${connection.type === "manual" ? `<button class="btn-danger" type="button" onclick="deleteConnection(${connection.id})">remover</button>` : ""}
            </div>
        </article>
    `).join("")
}

async function loadBookContext(bookId) {
    setContextLoadingState("book", true)
    setContextLoadingState("author", true)

    try {
        const context = await apiRequest(`/api/books/${bookId}/context`)
        renderContextCard("book", context.book, "Nenhum resumo encontrado para este livro.")
        renderContextCard("author", context.author, "Nenhum resumo encontrado para este autor.")
    } catch (error) {
        setContextLoadingState("book", false)
        setContextLoadingState("author", false)
        renderContextCard("book", null, "Nao foi possivel carregar o resumo do livro agora.")
        renderContextCard("author", null, "Nao foi possivel carregar o resumo do autor agora.")
    }
}

function setContextLoadingState(prefix, isLoading) {
    document.getElementById(`${prefix}-context-loading`)?.classList.toggle("hidden", !isLoading)
    document.getElementById(`${prefix}-context-empty`)?.classList.add("hidden")
    document.getElementById(`${prefix}-context-content`)?.classList.add("hidden")
}

function renderContextCard(prefix, summary, emptyMessage) {
    const loading = document.getElementById(`${prefix}-context-loading`)
    const empty = document.getElementById(`${prefix}-context-empty`)
    const content = document.getElementById(`${prefix}-context-content`)
    const title = document.getElementById(`${prefix}-context-title`)
    const text = document.getElementById(`${prefix}-context-text`)
    const link = document.getElementById(`${prefix}-context-link`)

    loading?.classList.add("hidden")

    if (!summary) {
        if (empty) {
            empty.textContent = emptyMessage
            empty.classList.remove("hidden")
        }
        content?.classList.add("hidden")
        return
    }

    if (title) {
        const languageLabel = summary.language ? ` (${summary.language.toUpperCase()})` : ""
        title.textContent = `${summary.title}${languageLabel}`
    }
    if (text) {
        text.textContent = summary.extract || ""
    }
    if (link && summary.url) {
        link.href = summary.url
        link.classList.remove("hidden")
    } else {
        link?.classList.add("hidden")
    }

    empty?.classList.add("hidden")
    content?.classList.remove("hidden")
}

async function deleteCurrentBook() {
    const book = appState.detail.book
    if (!book) return

    const confirmed = window.confirm(`Remover "${book.title}"?`)
    if (!confirmed) return

    try {
        await apiRequest(`/api/books/${book.id}`, { method: "DELETE" })
        showToast("Livro removido.")
        location.href = "/"
    } catch (error) {
        showToast(error.message, "error")
    }
}

async function updateStatus(status) {
    const book = appState.detail.book
    if (!book) return

    try {
        await apiRequest(`/api/books/${book.id}/status`, {
            method: "PUT",
            body: JSON.stringify({ status })
        })
        await loadBookDetail(book.id)
        showToast("Status atualizado.")
    } catch (error) {
        showToast(error.message, "error")
    }
}

function openConnectionModal() {
    appState.detail.selectedConnectionBook = null
    appState.detail.connectionResults = []
    document.getElementById("conn-search").value = ""
    document.getElementById("conn-note").value = ""
    document.getElementById("conn-results").innerHTML = ""
    const modal = document.getElementById("modal-connection")
    modal.classList.remove("hidden")
    modal.setAttribute("aria-hidden", "false")
}

function closeConnectionModal() {
    const modal = document.getElementById("modal-connection")
    if (!modal) return
    modal.classList.add("hidden")
    modal.setAttribute("aria-hidden", "true")
}

function handleConnectionSearch(event) {
    const query = event.target.value.trim()
    window.clearTimeout(appState.detail.searchTimer)

    if (!query) {
        document.getElementById("conn-results").innerHTML = ""
        return
    }

    appState.detail.searchTimer = window.setTimeout(async () => {
        try {
            const books = await apiRequest(`/api/books?q=${encodeURIComponent(query)}&sort=title&order=asc`)
            const currentBookId = appState.detail.book?.id
            appState.detail.connectionResults = books.filter(book => book.id !== currentBookId)
            renderConnectionResults()
        } catch (error) {
            showToast(error.message, "error")
        }
    }, 160)
}

function renderConnectionResults() {
    const container = document.getElementById("conn-results")
    if (!container) return

    if (!appState.detail.connectionResults.length) {
        container.innerHTML = `<div class="empty-inline">Nenhum livro encontrado.</div>`
        return
    }

    container.innerHTML = appState.detail.connectionResults.map(book => {
        const active = appState.detail.selectedConnectionBook?.id === book.id
        return `
            <button class="autocomplete-item ${active ? "active" : ""}" type="button" onclick="selectConnectionBook(${book.id})">
                <div>${escapeHtml(book.title)}</div>
                <div class="autocomplete-meta">${escapeHtml(book.author)}</div>
            </button>
        `
    }).join("")
}

function selectConnectionBook(bookId) {
    appState.detail.selectedConnectionBook = appState.detail.connectionResults.find(book => book.id === bookId) || null
    renderConnectionResults()
}

async function saveConnection() {
    const currentBook = appState.detail.book
    const targetBook = appState.detail.selectedConnectionBook

    if (!currentBook || !targetBook) {
        showToast("Escolha um livro para conectar.", "error")
        return
    }

    try {
        await apiRequest("/api/connections", {
            method: "POST",
            body: JSON.stringify({
                book_a_id: currentBook.id,
                book_b_id: targetBook.id,
                type: "manual",
                note: document.getElementById("conn-note").value.trim() || null
            })
        })

        closeConnectionModal()
        await loadBookDetail(currentBook.id)
        showToast("Conexão criada.")
    } catch (error) {
        showToast(error.message, "error")
    }
}

async function deleteConnection(connectionId) {
    const confirmed = window.confirm("Remover esta conexão manual?")
    if (!confirmed) return

    try {
        await apiRequest(`/api/connections/${connectionId}`, { method: "DELETE" })
        if (appState.detail.book) {
            await loadBookDetail(appState.detail.book.id)
        }
        showToast("Conexão removida.")
    } catch (error) {
        showToast(error.message, "error")
    }
}

function showToast(message, type = "success") {
    const container = document.getElementById("toast-container")
    if (!container) return

    const toast = document.createElement("div")
    toast.className = `toast ${type === "error" ? "toast-error" : ""}`
    toast.textContent = message
    container.appendChild(toast)

    window.setTimeout(() => {
        toast.remove()
    }, 3000)
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;")
}

window.updateStatus = updateStatus
window.closeConnectionModal = closeConnectionModal
window.saveConnection = saveConnection
window.selectConnectionBook = selectConnectionBook
window.deleteConnection = deleteConnection
