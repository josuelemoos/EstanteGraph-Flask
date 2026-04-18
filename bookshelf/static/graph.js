// ============================================================
// graph.js — Grafo 3D de conexões entre livros
// Usa: 3d-force-graph + Three.js via CDN
// ============================================================

let graphInstance = null
let graphData = null
let hoveredNode = null
let selectedNodeId = null
let allGenres = []

const activeFilters = {
    genre: true,
    tag: true,
    manual: true,
    genreId: null
}

document.addEventListener("DOMContentLoaded", init)

async function init() {
    if (!document.getElementById("graph-container")) return

    if (typeof THREE === "undefined" || typeof ForceGraph3D === "undefined") {
        showGraphMessage("Não foi possível carregar as bibliotecas do grafo 3D.")
        return
    }

    setupControls()
    setupPointerTracking()
    setupPanelClose()

    try {
        await Promise.all([loadGenres(), loadGraphData()])
        renderLegend()
        applyFilters()
        focusNodeFromQuery()
    } catch (error) {
        showGraphMessage(error.message || "Falha ao carregar o grafo.")
    }
}

async function loadGenres() {
    const response = await fetch("/api/genres")
    const payload = await response.json()

    if (!response.ok || payload.error) {
        throw new Error(payload.error || "Falha ao carregar gêneros")
    }

    allGenres = payload.data || []
    renderGenreOptions()
}

async function loadGraphData() {
    const response = await fetch("/api/graph")
    const payload = await response.json()

    if (!response.ok || payload.error) {
        throw new Error(payload.error || "Falha ao carregar dados do grafo")
    }

    graphData = normalizeGraphData(payload.data || { nodes: [], edges: [] })
    renderGraph(graphData)
}

function normalizeGraphData(data) {
    return {
        nodes: (data.nodes || []).map(node => ({
            ...node
        })),
        edges: (data.edges || []).map(edge => ({
            ...edge,
            source: Number(edge.source),
            target: Number(edge.target)
        }))
    }
}

function renderGraph(data) {
    const container = document.getElementById("graph-container")
    const height = Math.max(window.innerHeight - getNavbarHeight(), 520)

    graphInstance = ForceGraph3D()(container)
        .width(container.offsetWidth || window.innerWidth)
        .height(height)
        .graphData(buildRenderPayload(data.nodes, data.edges))
        .nodeLabel(node => `${node.title} — ${node.author}`)
        .nodeColor(node => node.color || "#888780")
        .nodeVal(node => node.size || 7)
        .nodeOpacity(0.92)
        .nodeThreeObject(node => {
            const group = new THREE.Group()

            const sphere = new THREE.Mesh(
                new THREE.SphereGeometry(node.size || 7, 18, 18),
                new THREE.MeshLambertMaterial({
                    color: node.color || "#888780",
                    transparent: true,
                    opacity: 0.88
                })
            )
            group.add(sphere)

            if (node.status === "read") {
                const ring = new THREE.Mesh(
                    new THREE.TorusGeometry((node.size || 7) * 1.35, 0.7, 10, 40),
                    new THREE.MeshLambertMaterial({ color: "#EF9F27" })
                )
                ring.rotation.x = Math.PI / 2
                group.add(ring)
            }

            const sprite = makeTextSprite(node.title)
            sprite.position.set(0, (node.size || 7) + 6, 0)
            group.add(sprite)

            return group
        })
        .nodeThreeObjectExtend(false)
        .linkColor(link => {
            if (link.type === "manual") return "#534AB7"
            if (link.type === "genre") return link.color || "#1D9E75"
            if (link.type === "tag") return "#BA7517"
            return "#888780"
        })
        .linkWidth(link => link.type === "manual" ? 2.4 : 1.15)
        .linkOpacity(0.62)
        .linkCurvature(link => link.type === "manual" ? 0.08 : 0)
        .linkDirectionalParticles(link => link.type === "manual" ? 3 : 0)
        .linkDirectionalParticleSpeed(0.004)
        .linkDirectionalParticleColor(link => link.type === "manual" ? "#534AB7" : link.color || "#BA7517")
        .onNodeHover(onNodeHover)
        .onNodeClick(onNodeClick)
        .onBackgroundClick(() => {
            resetHighlight()
            closePanel()
        })
        .backgroundColor("rgba(0,0,0,0)")
        .showNavInfo(false)
        .d3AlphaDecay(0.02)
        .d3VelocityDecay(0.3)
        .warmupTicks(100)
        .cooldownTicks(200)

    const chargeForce = graphInstance.d3Force("charge")
    const linkForce = graphInstance.d3Force("link")

    if (chargeForce) {
        chargeForce.strength(-120)
    }

    if (linkForce) {
        linkForce.distance(link => {
            if (link.type === "manual") return 80
            if (link.type === "genre") return 40
            return 60
        })
    }

    const ambientLight = new THREE.AmbientLight(0xffffff, 1.15)
    const keyLight = new THREE.DirectionalLight(0xffffff, 0.8)
    keyLight.position.set(80, 120, 100)
    graphInstance.scene().add(ambientLight)
    graphInstance.scene().add(keyLight)

    window.addEventListener("resize", handleResize)
}

function buildRenderPayload(nodes, edges) {
    return {
        nodes: nodes.map(node => ({ ...node })),
        links: edges.map(edge => ({
            ...edge,
            source: Number(normalizeLinkEnd(edge.source)),
            target: Number(normalizeLinkEnd(edge.target))
        }))
    }
}

function handleResize() {
    if (!graphInstance) return

    const container = document.getElementById("graph-container")
    graphInstance.width(container.offsetWidth || window.innerWidth)
    graphInstance.height(Math.max(window.innerHeight - getNavbarHeight(), 520))
}

function setupControls() {
    document.getElementById("show-genre")?.addEventListener("change", event => {
        activeFilters.genre = event.target.checked
        applyFilters()
    })

    document.getElementById("show-tag")?.addEventListener("change", event => {
        activeFilters.tag = event.target.checked
        applyFilters()
    })

    document.getElementById("show-manual")?.addEventListener("change", event => {
        activeFilters.manual = event.target.checked
        applyFilters()
    })

    document.getElementById("filter-genre")?.addEventListener("change", event => {
        const value = event.target.value
        activeFilters.genreId = value ? Number(value) : null
        applyFilters()
    })
}

function setupPointerTracking() {
    const container = document.getElementById("graph-container")
    const tooltip = document.getElementById("node-tooltip")

    if (!container || !tooltip) return

    container.addEventListener("mousemove", event => {
        if (!hoveredNode) return
        showTooltip(hoveredNode, event)
    })

    container.addEventListener("mouseleave", () => {
        hideTooltip()
    })
}

function setupPanelClose() {
    document.getElementById("panel-close")?.addEventListener("click", () => {
        resetHighlight()
        closePanel()
    })
}

function applyFilters() {
    if (!graphData || !graphInstance) return

    let filteredEdges = graphData.edges.filter(edge => {
        if (edge.type === "genre" && !activeFilters.genre) return false
        if (edge.type === "tag" && !activeFilters.tag) return false
        if (edge.type === "manual" && !activeFilters.manual) return false
        return true
    })

    let filteredNodes = [...graphData.nodes]

    if (activeFilters.genreId) {
        const relevantNodeIds = new Set(
            graphData.nodes
                .filter(node => (node.genre_ids || []).includes(activeFilters.genreId))
                .map(node => node.id)
        )

        filteredEdges = filteredEdges.filter(edge => relevantNodeIds.has(edge.source) || relevantNodeIds.has(edge.target))

        const connectedIds = new Set()
        filteredEdges.forEach(edge => {
            connectedIds.add(edge.source)
            connectedIds.add(edge.target)
        })

        filteredNodes = graphData.nodes.filter(node => connectedIds.has(node.id) || relevantNodeIds.has(node.id))
    }

    graphInstance.graphData(buildRenderPayload(filteredNodes, filteredEdges))
    resetHighlight()
    closePanel()
}

function onNodeHover(node) {
    hoveredNode = node || null

    if (!node) {
        hideTooltip()
    }
}

function onNodeClick(node) {
    if (!node || !graphInstance) return

    selectedNodeId = node.id

    const distance = 80
    const safeHypot = Math.hypot(node.x || 0, node.y || 0, node.z || 0) || 1
    const distRatio = 1 + distance / safeHypot

    graphInstance.cameraPosition(
        {
            x: (node.x || 0) * distRatio,
            y: (node.y || 0) * distRatio,
            z: (node.z || 0) * distRatio
        },
        node,
        1500
    )

    const connectedIds = new Set()
    const visibleLinks = graphInstance.graphData().links || []

    visibleLinks.forEach(link => {
        const sourceId = normalizeLinkEnd(link.source)
        const targetId = normalizeLinkEnd(link.target)

        if (sourceId === node.id || targetId === node.id) {
            connectedIds.add(sourceId)
            connectedIds.add(targetId)
        }
    })

    graphInstance
        .nodeOpacity(currentNode => currentNode.id === node.id || connectedIds.has(currentNode.id) ? 0.96 : 0.14)
        .linkOpacity(link => {
            const sourceId = normalizeLinkEnd(link.source)
            const targetId = normalizeLinkEnd(link.target)
            return sourceId === node.id || targetId === node.id ? 0.94 : 0.05
        })

    openPanel(node)
}

function showTooltip(node, event) {
    const tooltip = document.getElementById("node-tooltip")
    if (!tooltip || !node) return

    document.getElementById("tt-title").textContent = node.title || "Livro"
    document.getElementById("tt-author").textContent = node.author || ""
    document.getElementById("tt-rating").textContent = node.rating ? `Avaliação: ${node.rating}` : "Sem avaliação"
    document.getElementById("tt-genres").textContent = (node.genres || []).join(" · ")

    tooltip.style.left = `${event.clientX + 18}px`
    tooltip.style.top = `${event.clientY + 18}px`
    tooltip.classList.remove("hidden")
}

function hideTooltip() {
    document.getElementById("node-tooltip")?.classList.add("hidden")
}

async function openPanel(node) {
    const panel = document.getElementById("node-panel")
    if (!panel) return

    panel.classList.remove("hidden")
    renderPanelSkeleton(node)

    try {
        const response = await fetch(`/api/books/${node.id}`)
        const payload = await response.json()

        if (!response.ok || payload.error) {
            throw new Error(payload.error || "Falha ao carregar detalhes do livro")
        }

        renderPanel(payload.data)
    } catch (error) {
        document.getElementById("panel-review").textContent = error.message
    }
}

function renderPanelSkeleton(node) {
    document.getElementById("panel-cover").style.backgroundImage = "none"
    document.getElementById("panel-cover").style.backgroundColor = `${node.color || "#888780"}22`
    document.getElementById("panel-cover").innerHTML = `<span class="panel-cover-initials">${escapeHtml((node.title || "??").slice(0, 2).toUpperCase())}</span>`
    document.getElementById("panel-title").textContent = node.title || "Livro"
    document.getElementById("panel-author").textContent = node.author || ""
    document.getElementById("panel-rating").textContent = node.rating ? `★ ${node.rating}` : "Sem avaliação"
    document.getElementById("panel-status").innerHTML = `<span class="status-badge status-${node.status || "want"}">${statusLabel(node.status)}</span>`
    document.getElementById("panel-genres").innerHTML = (node.genres || []).map(genre => `<span class="genre-pill">${escapeHtml(genre)}</span>`).join("")
    document.getElementById("panel-tags").innerHTML = (node.tags || []).map(tag => `<span class="tag-pill">${escapeHtml(tag)}</span>`).join("")
    document.getElementById("panel-review").textContent = "Carregando detalhes..."
    document.getElementById("panel-link").href = `/books/${node.id}`
}

function renderPanel(book) {
    const primaryGenre = book.genres?.[0]
    const cover = document.getElementById("panel-cover")

    if (book.cover_url) {
        cover.style.backgroundImage = `url("${String(book.cover_url).replaceAll('"', '\\"')}")`
        cover.style.backgroundColor = "transparent"
        cover.innerHTML = ""
    } else {
        cover.style.backgroundImage = "none"
        cover.style.backgroundColor = `${primaryGenre?.color_hex || "#888780"}22`
        cover.innerHTML = `<span class="panel-cover-initials">${escapeHtml((book.title || "??").slice(0, 2).toUpperCase())}</span>`
    }

    document.getElementById("panel-title").textContent = book.title || "Livro"
    document.getElementById("panel-author").textContent = [book.author, book.year].filter(Boolean).join(" · ")
    document.getElementById("panel-rating").textContent = book.rating ? `★ ${book.rating}` : "Sem avaliação"
    document.getElementById("panel-status").innerHTML = `<span class="status-badge status-${book.status || "want"}">${statusLabel(book.status)}</span>`
    document.getElementById("panel-genres").innerHTML = (book.genres || []).map(genre => `
        <span class="genre-pill" style="background:${genre.color_hex}22;color:${genre.color_hex}">${escapeHtml(genre.name)}</span>
    `).join("")
    document.getElementById("panel-tags").innerHTML = (book.tags || []).map(tag => `<span class="tag-pill">${escapeHtml(tag)}</span>`).join("")
    document.getElementById("panel-review").textContent = book.review || "Sem resenha cadastrada."
    document.getElementById("panel-link").href = `/books/${book.id}`
}

function closePanel() {
    document.getElementById("node-panel")?.classList.add("hidden")
}

function resetHighlight() {
    selectedNodeId = null

    if (!graphInstance) return

    graphInstance
        .nodeOpacity(0.92)
        .linkOpacity(0.62)
}

function renderGenreOptions() {
    const select = document.getElementById("filter-genre")
    if (!select) return

    select.innerHTML = `
        <option value="">todos</option>
        ${allGenres.map(genre => `<option value="${genre.id}">${escapeHtml(genre.name)}</option>`).join("")}
    `
}

function renderLegend() {
    const container = document.getElementById("legend-genres")
    if (!container) return

    container.innerHTML = allGenres.map(genre => `
        <div class="legend-item">
            <span class="legend-dot" style="background:${genre.color_hex}"></span>
            <span>${escapeHtml(genre.name)}</span>
        </div>
    `).join("")
}

function focusNodeFromQuery() {
    const page = document.querySelector(".graph-page")
    const focusId = Number(page?.dataset.focus || "")
    if (!focusId || !graphData) return

    const node = graphData.nodes.find(item => item.id === focusId)
    if (!node) return

    window.setTimeout(() => {
        onNodeClick(node)
    }, 600)
}

function showGraphMessage(message) {
    const container = document.getElementById("graph-container")
    if (!container) return

    container.innerHTML = `<div class="graph-empty">${escapeHtml(message)}</div>`
}

function normalizeLinkEnd(value) {
    return typeof value === "object" ? value.id : value
}

function makeTextSprite(text) {
    const canvas = document.createElement("canvas")
    canvas.width = 256
    canvas.height = 64
    const context = canvas.getContext("2d")

    if (!context) {
        const sprite = new THREE.Sprite(new THREE.SpriteMaterial())
        sprite.scale.set(1, 1, 1)
        return sprite
    }

    context.fillStyle = "rgba(0,0,0,0.62)"
    drawRoundedRect(context, 4, 4, canvas.width - 8, canvas.height - 8, 10)
    context.fill()

    context.font = "bold 20px sans-serif"
    context.fillStyle = "#ffffff"
    context.textAlign = "center"
    context.textBaseline = "middle"

    const maxWidth = canvas.width - 20
    let displayText = text || ""

    while (context.measureText(displayText).width > maxWidth && displayText.length > 3) {
        displayText = `${displayText.slice(0, -4)}...`
    }

    context.fillText(displayText, canvas.width / 2, canvas.height / 2)

    const texture = new THREE.CanvasTexture(canvas)
    texture.needsUpdate = true
    const material = new THREE.SpriteMaterial({ map: texture, transparent: true })
    const sprite = new THREE.Sprite(material)
    sprite.scale.set(30, 8, 1)
    return sprite
}

function drawRoundedRect(context, x, y, width, height, radius) {
    context.beginPath()
    context.moveTo(x + radius, y)
    context.lineTo(x + width - radius, y)
    context.quadraticCurveTo(x + width, y, x + width, y + radius)
    context.lineTo(x + width, y + height - radius)
    context.quadraticCurveTo(x + width, y + height, x + width - radius, y + height)
    context.lineTo(x + radius, y + height)
    context.quadraticCurveTo(x, y + height, x, y + height - radius)
    context.lineTo(x, y + radius)
    context.quadraticCurveTo(x, y, x + radius, y)
    context.closePath()
}

function getNavbarHeight() {
    return document.querySelector(".navbar")?.offsetHeight || 80
}

function statusLabel(status) {
    return {
        want: "quero ler",
        reading: "lendo",
        read: "lido"
    }[status] || "quero ler"
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;")
}
