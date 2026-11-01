/* GK.ui.recipes: the Receitas screen (#recipes). Browse every item (own search box, category and station
   chips with counts, hidden-items toggle, 60 rows per page) and an item detail (recipes with inputs, unlock,
   mastery, time/energy, by-products; group members; how to obtain; "Usado em"; add to goals; pick the
   recipe the planner uses). Only the bare #recipes hash reaches the page, so the open item lives in module
   state and in sessionStorage (gk2-recipes-view).
   Owns: [data-panel="recipes"] and the "recipes" route.
   Exposes: GK.ui.recipes.{mount, render, open(itemId, {from})}; registered as a panel. open(id, {from: "plan"})
   (the planner's "i" buttons, the Tecnologias unlock rows) shows the detail with a "← Voltar: <screen>" button that
   returns to that screen at its old scroll position and focuses the button that opened the detail.
   1.6.0 (cortes 7, 12, 13, 18): no top hint; rows say "Construir no Cemitério" (GK.ui.fmt.buildLabel) and the recipe
   count only when > 1; "Mostrar itens ocultos" at the end of the list; "Também em" once when every recipe shares it;
   no "Usado em" section when empty; no plain toast when the first goal replaces the example (search.js shows it).
   Ficha completa (docs/revisao-ux/protos/ficha-item.html): "Quem compra" (items[].sell / .price / .fix),
   "Estudar" (items[].study + the global "Já estudei", state.studied) and "Pedido em" (items[].asked: quests, town
   restorations and orders), folded by default (spoiler). Each block only when the item has the data.
   1.8.0: the phone's back gesture closes the detail (GK.router.detailHistory: an entry per item opened on this
   screen; "← Voltar" and "Ver lista" drop them); a list row with no recipe says "Coleta ou compra" (rc.raw); a name
   shared by two items shows the other language's name small (GK.ui.fmt.otherName); mastery level 0 shows no "0".
   1.8.0, receitas agrupadas (protos/receitas-agrupadas): "Como fabricar" follows GK.calc.recipeGroups: one card for
   the recipes that differ only in one ingredient (its grade picked in the card: bronze / prata / ouro, or "E mais um
   destes" rows); a tap on an option sets the planner's recipe (no "Usar" button there); the circular recipes fold at
   the end ("Melhorar a qualidade · N"). A graded item shows its name without "(prata)", the star on its icon
   (GK.util.slot) and the grade word on the line below (list rows, ingredient lines, "Usado em"); bronze, prata, ouro
   in that order (GK.data.gradeSort). "Quem compra": pixel coins (recipes.css).
*/
GK.i18n.add({
  pt: {
    "rc.tab": "Receitas",
    "rc.title": "Receitas",
    "rc.searchLabel": "Buscar item nas receitas",
    "rc.placeholder": "Buscar item",
    "rc.clear": "Limpar busca",
    "rc.filters": "Filtros",
    "rc.filtersOn.one": "{n} ativo",
    "rc.filtersOn.other": "{n} ativos",
    "rc.cat": "Categoria",
    "rc.station": "Estação",
    "rc.all": "Ver todas ({n})",
    "rc.less": "Ver menos",
    "rc.noCat": "Sem categoria",
    "rc.noRecipe": "Sem receita (coleta, compra…)",
    "rc.clearFilters": "Limpar filtros",
    "rc.removeFilter": "Remover filtro: {name}",
    "rc.count.one": "{n} item",
    "rc.count.other": "{n} itens",
    "rc.none": "Nenhum item com esses filtros.",
    "rc.noneQ": "Nada encontrado para “{q}”. Tente outro nome, em português ou inglês, ou limpe os filtros.",
    "rc.more": "Mostrar mais ({n} restantes)",
    "rc.hiddenShow": "Mostrando itens ocultos",
    "rc.hiddenMore": "Mostrar itens ocultos (+{n})",
    "rc.hiddenNone": "Mostrar itens ocultos",
    "rc.recipes.one": "{n} receita",
    "rc.recipes.other": "{n} receitas",
    "rc.raw": "Coleta ou compra",
    "rc.open": "Ver receitas de {name}",
    "rc.back": "← Voltar à lista",
    "rc.backTo": "← Voltar: {name}",
    "rc.toList": "Lista",
    "rc.unofficial": "não oficial",
    "rc.unofficialTitle": "Tradução não oficial do nome",
    "rc.edited": "editado",
    "rc.editedTitle": "Nome editado por você",
    "rc.hidden": "oculto",
    "rc.hiddenTitle": "Oculto na wiki ou não é um item de verdade",
    "rc.unobt": "não obtenível",
    "rc.unobtTitle": "Nada fornece este item na versão atual do jogo",
    "rc.kind.building": "Construção",
    "rc.kind.station": "Estação de trabalho",
    "rc.kind.group": "Grupo de itens",
    "rc.kind.quality-variant": "Variante de qualidade",
    "rc.kind.virtual": "Item virtual",
    "rc.kind.action": "Ação ou efeito",
    "rc.addGoal": "Adicionar às metas",
    "rc.qty": "Quantidade de {name}",
    "rc.dec": "Diminuir quantidade",
    "rc.inc": "Aumentar quantidade",
    "rc.inGoals": "Nas metas: {n}",
    "rc.toPlan": "Ver no Planejador",
    "rc.obtain": "Como obter",
    "rc.members": "Qualquer um destes serve",
    "rc.memberOf": "Faz parte de",
    "rc.runes": "Runas",
    "rc.recipesTitle": "Como fabricar",
    "rc.noRecipes": "Nenhuma receita fabrica este item: ele é coletado, comprado ou obtido de outra forma.",
    "rc.qPick": "Qualidade do ingrediente",
    "rc.qMore": "E mais um destes",
    "rc.inUseQ": "Em uso no planejador: {what}",
    "rc.cycT": "Melhorar a qualidade",
    "rc.cycD": "Receitas que usam o próprio {name}",
    "rc.recipeN": "Receita {l}",
    "rc.makes": "rende {n}",
    "rc.makesVar": "rendimento varia",
    "rc.bonusYield": "Rende {n} com {perk}",
    "rc.bonusAdd": "Rende +{n} com {perk}",
    "rc.bonusOn": "vantagem ligada",
    "rc.makesNote": "Rende: {note}",
    "rc.star": "Qualidade: prata com {silver} ciclos bem-sucedidos, ouro com {gold}",
    "rc.noInputs": "Sem ingredientes",
    "rc.alt": "Também em: {names}",
    "rc.altAll": "Todas também em: {names}",
    "rc.tech": "Requer {tech}",
    "rc.quest": "Missão: {tech}",
    "rc.perk": "Vantagem: {tech}",
    "rc.mastery": "Maestria: {type} {level}",
    "rc.ext": "Extensão na estação: {ext}",
    "rc.time.one": "Tempo: {n} ciclo",
    "rc.time.other": "Tempo: {n} ciclos",
    "rc.energy": "Energia: {n} por ciclo",
    "rc.energyTotal": "Energia: {n} por ciclo ({total} no total)",
    "rc.runesNeed": "Runas exigidas",
    "rc.extra": "Subprodutos (não somados no plano)",
    "rc.example": "mistura de exemplo",
    "rc.exampleTitle": "Alquimia: qualquer combinação de ingredientes com as mesmas runas funciona",
    "rc.hiddenRecipe": "oculta na wiki",
    "rc.cyc": "circular",
    "rc.noexp": "colheita",
    "rc.default": "padrão",
    "rc.inUse": "Em uso no planejador",
    "rc.use": "Usar esta receita no planejador",
    "rc.useDefault": "Voltar à receita padrão",
    "rc.used": "O planejador vai usar {station} para {name}",
    "rc.usedDefault": "Receita padrão de volta para {name}",
    "rc.usedIn": "Usado em",
    "rc.uses": "usa {n}",
    "rc.via": "via {group}",
    "rc.madeHere": "Fabricado aqui",
    "rc.showAll": "Mostrar todos ({n})",
    "rc.added": "Adicionado às metas: {name} ×{n}",
    "rc.bumped": "{name}: agora {n} nas metas",
    "rune.red": "Vermelha",
    "rune.green": "Verde",
    "rune.blue": "Azul",
  },
  en: {
    "rc.tab": "Recipes",
    "rc.title": "Recipes",
    "rc.searchLabel": "Search items in the recipes",
    "rc.placeholder": "Search items",
    "rc.clear": "Clear search",
    "rc.filters": "Filters",
    "rc.filtersOn.one": "{n} on",
    "rc.filtersOn.other": "{n} on",
    "rc.cat": "Category",
    "rc.station": "Station",
    "rc.all": "Show all ({n})",
    "rc.less": "Show fewer",
    "rc.noCat": "No category",
    "rc.noRecipe": "No recipe (gather, buy…)",
    "rc.clearFilters": "Clear filters",
    "rc.removeFilter": "Remove filter: {name}",
    "rc.count.one": "{n} item",
    "rc.count.other": "{n} items",
    "rc.none": "No items match these filters.",
    "rc.noneQ": "Nothing found for “{q}”. Try another name, in English or Portuguese, or clear the filters.",
    "rc.more": "Show more ({n} left)",
    "rc.hiddenShow": "Showing hidden items",
    "rc.hiddenMore": "Show hidden items (+{n})",
    "rc.hiddenNone": "Show hidden items",
    "rc.recipes.one": "{n} recipe",
    "rc.recipes.other": "{n} recipes",
    "rc.raw": "Gather or buy",
    "rc.open": "See the recipes for {name}",
    "rc.back": "← Back to the list",
    "rc.backTo": "← Back: {name}",
    "rc.toList": "List",
    "rc.unofficial": "unofficial",
    "rc.unofficialTitle": "Unofficial name translation",
    "rc.edited": "edited",
    "rc.editedTitle": "Name edited by you",
    "rc.hidden": "hidden",
    "rc.hiddenTitle": "Hidden on the wiki, or not a real item",
    "rc.unobt": "unobtainable",
    "rc.unobtTitle": "Nothing gives this item in the current game version",
    "rc.kind.building": "Building",
    "rc.kind.station": "Work station",
    "rc.kind.group": "Item group",
    "rc.kind.quality-variant": "Quality variant",
    "rc.kind.virtual": "Virtual item",
    "rc.kind.action": "Action or effect",
    "rc.addGoal": "Add to goals",
    "rc.qty": "Amount of {name}",
    "rc.dec": "Decrease amount",
    "rc.inc": "Increase amount",
    "rc.inGoals": "In goals: {n}",
    "rc.toPlan": "See in the Planner",
    "rc.obtain": "How to get it",
    "rc.members": "Any of these works",
    "rc.memberOf": "Part of",
    "rc.runes": "Runes",
    "rc.recipesTitle": "How to make it",
    "rc.noRecipes": "No recipe makes this item: it is gathered, bought or obtained some other way.",
    "rc.qPick": "Ingredient quality",
    "rc.qMore": "Plus one of these",
    "rc.inUseQ": "Used by the planner: {what}",
    "rc.cycT": "Improve quality",
    "rc.cycD": "Recipes that use the {name} itself",
    "rc.recipeN": "Recipe {l}",
    "rc.makes": "makes {n}",
    "rc.makesVar": "yield varies",
    "rc.bonusYield": "Makes {n} with {perk}",
    "rc.bonusAdd": "Makes +{n} with {perk}",
    "rc.bonusOn": "perk on",
    "rc.makesNote": "Makes: {note}",
    "rc.star": "Quality: silver at {silver} successful ticks, gold at {gold}",
    "rc.noInputs": "No ingredients",
    "rc.alt": "Also at: {names}",
    "rc.altAll": "All also at: {names}",
    "rc.tech": "Needs {tech}",
    "rc.quest": "Quest: {tech}",
    "rc.perk": "Perk: {tech}",
    "rc.mastery": "Mastery: {type} {level}",
    "rc.ext": "Station extension: {ext}",
    "rc.time.one": "Time: {n} tick",
    "rc.time.other": "Time: {n} ticks",
    "rc.energy": "Energy: {n} per tick",
    "rc.energyTotal": "Energy: {n} per tick ({total} in total)",
    "rc.runesNeed": "Runes needed",
    "rc.extra": "By-products (not counted in the plan)",
    "rc.example": "example mix",
    "rc.exampleTitle": "Alchemy: any mix of ingredients with the same runes works",
    "rc.hiddenRecipe": "hidden on the wiki",
    "rc.cyc": "circular",
    "rc.noexp": "harvest",
    "rc.default": "default",
    "rc.inUse": "Used by the planner",
    "rc.use": "Use this recipe in the planner",
    "rc.useDefault": "Back to the default recipe",
    "rc.used": "The planner will use {station} for {name}",
    "rc.usedDefault": "Default recipe restored for {name}",
    "rc.usedIn": "Used in",
    "rc.uses": "uses {n}",
    "rc.via": "via {group}",
    "rc.madeHere": "Made here",
    "rc.showAll": "Show all ({n})",
    "rc.added": "Added to goals: {name} ×{n}",
    "rc.bumped": "{name}: now {n} in goals",
    "rune.red": "Red",
    "rune.green": "Green",
    "rune.blue": "Blue",
  },
});
// "Onde conseguir" (items[].where) and the game-style use tooltip (items[].use, .stack), from data/facts.json
GK.i18n.add({
  pt: {
    "rc.where": "Onde conseguir",
    "rc.whereMore": "mais {n}",
    "rc.whereMoreLabel": "Mostrar mais {n} fontes",
    "rc.questOnly": "Só de missão",
    "rc.questOnlyTitle": "Nenhuma loja, coleta ou receita dá este item: só missões",
    "rc.w.buy": "Comprar", "rc.w.fish": "Pescar", "rc.w.gather": "Coletar", "rc.w.quest": "Missão",
    "rc.w.battle": "Batalha", "rc.w.chest": "Baú", "rc.w.found": "Achar", "rc.w.looter": "Saqueadores",
    "rc.w.autopsy": "Autópsia", "rc.w.burial": "Recompensa", "rc.w.container": "Abrir", "rc.w.town": "Restauração",
    "rc.w.study": "Mesa de estudo", "rc.w.church": "Igreja", "rc.w.start": "Início", "rc.w.outfit": "Traje",
    "rc.w.resurrect": "Ressurreição", "rc.w.character": "Entrega",
    "rc.w.level": "desde o nível {n}",
    "rc.w.talk": "só conversando, sem loja",
    "rc.w.noBait": "sem isca",
    "rc.w.dayNight": "dia {d}% · noite {n}%",
    "rc.w.allDay": "dia e noite {d}%",
    "rc.w.chestOnce": "uma vez, no início do jogo",
    "rc.w.once": "uma vez",
    "rc.w.unofficialTitle": "Nome sem tradução oficial do jogo",
    "rc.stack": "Pilha: {n} por espaço.",
    "rc.stackOne": "Não empilha: um por espaço.",
    "rc.stackTitle": "Pilha máxima: {n}",
    "rc.useLbl": "Efeito de uso:",
    "rc.energyName": "Energia",
    "rc.insanityName": "insanidade",
    "rc.bar": "{n} de 100 da barra de energia",
    "rc.barLabel": "Enche {n} dos 100 pontos da barra de energia",
    "rc.boost": "{v} com {buff}",
    "rc.lasts": "Dura {t}.",
    "rc.restart": "Usar outro reinicia o tempo.",
    "rc.descUnofficial": "Descrição da wiki, sem texto oficial do jogo",
  },
  en: {
    "rc.where": "Where to get it",
    "rc.whereMore": "{n} more",
    "rc.whereMoreLabel": "Show {n} more sources",
    "rc.questOnly": "Quest only",
    "rc.questOnlyTitle": "No shop, gathering or recipe gives this item: only quests",
    "rc.w.buy": "Buy", "rc.w.fish": "Fish", "rc.w.gather": "Gather", "rc.w.quest": "Quest",
    "rc.w.battle": "Battle", "rc.w.chest": "Chest", "rc.w.found": "Find", "rc.w.looter": "Looters",
    "rc.w.autopsy": "Autopsy", "rc.w.burial": "Reward", "rc.w.container": "Open", "rc.w.town": "Restoration",
    "rc.w.study": "Study Table", "rc.w.church": "Church", "rc.w.start": "Start", "rc.w.outfit": "Outfit",
    "rc.w.resurrect": "Resurrection", "rc.w.character": "Delivered by",
    "rc.w.level": "from trader level {n}",
    "rc.w.talk": "in conversation, no shop",
    "rc.w.noBait": "no bait",
    "rc.w.dayNight": "day {d}% · night {n}%",
    "rc.w.allDay": "day and night {d}%",
    "rc.w.chestOnce": "once, at the start of the game",
    "rc.w.once": "once",
    "rc.w.unofficialTitle": "No official game translation for this name",
    "rc.stack": "Stack: {n} per slot.",
    "rc.stackOne": "Does not stack: one per slot.",
    "rc.stackTitle": "Max stack: {n}",
    "rc.useLbl": "Effect on use:",
    "rc.energyName": "Energy",
    "rc.insanityName": "insanity",
    "rc.bar": "{n} of the 100-point energy bar",
    "rc.barLabel": "Fills {n} of the 100 points of the energy bar",
    "rc.boost": "{v} with {buff}",
    "rc.lasts": "Lasts {t}.",
    "rc.restart": "Using another restarts the timer.",
    "rc.descUnofficial": "Wiki description, no official game text",
  },
});

// "Quem compra", "Estudar", "Pedido em" (items[].sell / .price / .fix / .study / .asked, data/facts.json; ficha completa)
GK.i18n.add({
  pt: {
    "rc.sell": "Quem compra",
    "rc.sellInfo": "Sobre o preço",
    "rc.sellNote": "Quanto cada um paga por 1 com o estoque normal dele (do nível 1 ao 3 do comerciante). Se ele já tem muitos, ou se você vende vários de uma vez, o preço cai; sem estoque, sobe até o preço base (o “até”). Peixes têm preço fixo. Curtidas: o máximo por semana vendendo para ele.",
    "rc.sellNoteFix": "Preço fixo: quem compra paga sempre {n}, com ou sem estoque, como nos peixes.",
    "rc.sellUpTo": "até {v}",
    "rc.sellFix": "preço fixo",
    "rc.sellLikes": "até +{n} curtidas por semana",
    "rc.sellLikesFrom": "curtidas a partir do nível {lv}: até +{n} por semana",
    "rc.sellLikesAny": "dá curtidas",
    "rc.sellLikesAnyFrom": "dá curtidas a partir do nível {lv}",
    "rc.sellLevel": "compra a partir do nível {n}",
    "rc.coin.g": "ouro", "rc.coin.s": "prata", "rc.coin.b": "bronze",
    "rc.study": "Estudar",
    "rc.studied": "Já estudei",
    "rc.studiedLabel": "Já estudei: {name}",
    "rc.studyNote": "Uma vez só, na Mesa de Estudo; o item não é gasto.",
    "rc.studyCost": "Custa {sci} de Ciência.",
    "rc.studyCostFaith": "Custa {sci} de Ciência e {faith} de Fé.",
    "rc.asked": "Pedido em",
    "rc.askedShowQ.one": "Mostrar 1 missão",
    "rc.askedShowQ.other": "Mostrar as {n} missões",
    "rc.askedShowO.one": "Mostrar 1 uso no povoado",
    "rc.askedShowO.other": "Mostrar {n} usos no povoado",
    "rc.askedShowQO.one": "Mostrar 1 missão e {o} usos no povoado",
    "rc.askedShowQO.other": "Mostrar {n} missões e {o} usos no povoado",
    "rc.askedHide": "Esconder",
    "rc.askedWarn": "Pode revelar parte da história (spoiler).",
    "rc.askedQ": "Missões",
    "rc.askedTown": "Restauração do povoado",
    "rc.askedOrder": "Encomendas do povoado",
    "rc.askedLevel": "nível {n}",
    "rc.askedLikes": "+{n} curtidas",
  },
  en: {
    "rc.sell": "Who buys it",
    "rc.sellInfo": "About the price",
    "rc.sellNote": "What each one pays for 1 at its usual stock (trader levels 1 to 3). If it already holds many, or you sell several at once, the price drops; short of stock, it rises up to the base price (the “up to”). Fish have a fixed price. Likes: the most a week from selling to it.",
    "rc.sellNoteFix": "Fixed price: every buyer always pays {n}, with or without stock, like fish.",
    "rc.sellUpTo": "up to {v}",
    "rc.sellFix": "fixed price",
    "rc.sellLikes": "up to +{n} Likes a week",
    "rc.sellLikesFrom": "Likes from level {lv}: up to +{n} a week",
    "rc.sellLikesAny": "gives Likes",
    "rc.sellLikesAnyFrom": "gives Likes from level {lv}",
    "rc.sellLevel": "buys from level {n}",
    "rc.coin.g": "gold", "rc.coin.s": "silver", "rc.coin.b": "bronze",
    "rc.study": "Study",
    "rc.studied": "Studied",
    "rc.studiedLabel": "Studied: {name}",
    "rc.studyNote": "Once only, at the Study Table; the item is kept.",
    "rc.studyCost": "Costs {sci} Science.",
    "rc.studyCostFaith": "Costs {sci} Science and {faith} Faith.",
    "rc.asked": "Asked for in",
    "rc.askedShowQ.one": "Show 1 quest",
    "rc.askedShowQ.other": "Show the {n} quests",
    "rc.askedShowO.one": "Show 1 use in the Town",
    "rc.askedShowO.other": "Show {n} uses in the Town",
    "rc.askedShowQO.one": "Show 1 quest and {o} uses in the Town",
    "rc.askedShowQO.other": "Show {n} quests and {o} uses in the Town",
    "rc.askedHide": "Hide",
    "rc.askedWarn": "May reveal part of the story (spoiler).",
    "rc.askedQ": "Quests",
    "rc.askedTown": "Town restoration",
    "rc.askedOrder": "Town orders",
    "rc.askedLevel": "level {n}",
    "rc.askedLikes": "+{n} Likes",
  },
});

GK.ui.recipes = (function () {
  const { t, name, num, edited } = GK.i18n, { esc, slot } = GK.util;
  const PAGE = 60, CHIPS = 8, LIST_CAP = 40, SKEY = "gk2-recipes-view";
  const UNOFFICIAL = { guess: 1, machine: 1, missing: 1 };
  const BUILD = { id: "build", i18n: "station.build" }, NONE = { id: "none", i18n: "rc.noRecipe" }, NOCAT = { i18n: "rc.noCat" };

  let root, browseEl, detailEl, input, clearBtn, listEl, chipsEl, metaEl, moreEl, filtersEl, hiddenEl;
  let IX = null;                 // lazy index, built on the first visit
  // view state (also in sessionStorage)
  const V = { item: null, stack: [], q: "", cat: null, st: null, from: null };   // from: route that opened the detail
  let fromScroll = 0, returnTo = null, pendingFocus = false;
  let shown = PAGE, results = [], expanded = { cat: false, st: false };
  let addQty = 1, usedAll = false, hereAll = false, whereAll = false, listScroll = 0, sortCache = { key: "", ids: [] };
  let askedOpen = false;         // "Pedido em" unfolded (folded again when another item opens)
  let cycOpen = false;           // "Melhorar a qualidade" unfolded (idem)
  let hist = null;               // GK.router.detailHistory: the back gesture closes the detail (mount)

  /* ---------- persistence ---------- */
  function save() {
    try { window.sessionStorage.setItem(SKEY, JSON.stringify(V)); } catch (e) { /* storage blocked */ }
  }
  function restore() {
    try {
      const o = JSON.parse(window.sessionStorage.getItem(SKEY) || "null");
      if (!o || typeof o !== "object") return;
      const D = GK.data.get();
      if (typeof o.q === "string") V.q = o.q.slice(0, 80);
      if (typeof o.cat === "string") V.cat = o.cat;
      if (typeof o.st === "string") V.st = o.st;
      if (typeof o.item === "string" && D.items[o.item]) V.item = o.item;
      if (Array.isArray(o.stack)) V.stack = o.stack.filter((id) => typeof id === "string" && D.items[id]).slice(-30);
      if (typeof o.from === "string" && o.from !== "recipes" && GK.router.TABS.some((r) => r.id === o.from) && V.item) V.from = o.from;
    } catch (e) { /* corrupt or blocked */ }
  }
  const saveSoon = GK.util.debounce(save, 300);

  /* ---------- index (lazy) ---------- */
  const stKey = (s) => (!s ? "none" : s.build ? "build" : s.id);
  function buildIndex() {
    const D = GK.data.get();
    IX = { rows: {}, cats: {}, stations: { build: BUILD, none: NONE }, byStation: {}, memberOf: {} };
    for (const it of Object.values(D.items)) {
      if (it.stub) continue;
      const rs = GK.data.recipesFor(it.id), st = new Set();
      for (const r of rs) { st.add(stKey(r.station)); r.alt.forEach((a) => st.add(stKey(a))); }
      if (!rs.length) st.add("none");
      for (const k of st) if (!IX.stations[k]) IX.stations[k] = D.stations[k] || { id: k, pt: k, en: k };
      const cat = it.cat ? it.cat.en : "";
      if (!(cat in IX.cats)) IX.cats[cat] = it.cat || NOCAT;
      const main = (it.defaultRecipe && D.recipeById[it.defaultRecipe]) || rs[0] || null;
      IX.rows[it.id] = { id: it.id, cat, st: [...st], n: rs.length, main: main ? main.station : null, hidden: it.hidden };
      if (it.members) for (const m of it.members) (IX.memberOf[m] = IX.memberOf[m] || []).push(it.id);
    }
    for (const r of D.recipes) {
      const ids = new Set([r.station.id].concat(r.alt.map((a) => a.id)));
      for (const id of ids) (IX.byStation[id] = IX.byStation[id] || []).push(r);
    }
  }

  /* ---------- browse ---------- */
  function sortedIds(state) {
    const lang = GK.i18n.lang(), ov = state.overrides && state.overrides[lang];
    const key = lang + "|" + (ov ? JSON.stringify(ov) : "");
    if (sortCache.key === key) return sortCache.ids;
    const D = GK.data.get(), coll = new Intl.Collator(GK.i18n.meta(lang).locale, { sensitivity: "base", numeric: true });
    const label = {};
    for (const id in IX.rows) label[id] = name(D.items[id], state.overrides);
    const ids = Object.keys(IX.rows).sort((a, b) => coll.compare(label[a], label[b]));
    GK.data.gradeSort(ids, (id) => GK.data.family(D.items[id]), (id) => GK.data.GRADE_RANK[D.items[id].grade]);
    sortCache = { key, ids };
    return sortCache.ids;
  }
  function compute(state) {
    const D = GK.data.get(), q = V.q.trim();
    const base = q
      ? GK.calc.search(q, D, { lang: GK.i18n.lang(), overrides: state.overrides, showHidden: true, limit: 100000 }).results.map((r) => r.id)
      : sortedIds(state);
    const catN = {}, stN = {}, out = [];
    let hiddenN = 0;
    for (const id of base) {
      const row = IX.rows[id];
      if (!row) continue;
      const okCat = !V.cat || row.cat === V.cat, okSt = !V.st || row.st.indexOf(V.st) >= 0;
      if (row.hidden && !state.showHidden) { if (okCat && okSt) hiddenN++; continue; }
      if (okSt) catN[row.cat] = (catN[row.cat] || 0) + 1;
      if (okCat) for (const k of row.st) stN[k] = (stN[k] || 0) + 1;
      if (okCat && okSt) out.push(row);
    }
    return { rows: out, catN, stN, hiddenN };
  }
  function chips(kind, counts, labels, selected, state) {
    const lbl = (k) => name(labels[k] || { pt: k, en: k }, state.overrides);
    let list = Object.keys(counts).filter((k) => counts[k] > 0 || k === selected);
    if (selected != null && list.indexOf(selected) < 0) list.push(selected);
    list.sort((a, b) => (b === selected) - (a === selected) || (counts[b] || 0) - (counts[a] || 0) || lbl(a).localeCompare(lbl(b)));
    const total = list.length, open = expanded[kind];
    if (!open) list = list.slice(0, CHIPS);
    const html = list.map((k) => `<button type="button" class="chip" data-chip="${kind}" data-key="${esc(k)}" aria-pressed="${k === selected}">${esc(lbl(k))} <span class="chip-n">${num(counts[k] || 0)}</span></button>`).join("");
    const more = total > CHIPS ? `<button type="button" class="chip chip-more" data-chip-more="${kind}" aria-expanded="${open}">${esc(open ? t("rc.less") : t("rc.all", { n: total }))}</button>` : "";
    return `<div class="chip-group" role="group" aria-labelledby="rc-${kind}-h"><h3 class="chip-h" id="rc-${kind}-h">${esc(t(kind === "cat" ? "rc.cat" : "rc.station"))}</h3><div class="chips">${html}${more}</div></div>`;
  }
  // a graded item in a list: the name without "(prata)" and the grade word for the line below (the star is on the
  // icon; colour alone is not enough). grade = a recipe line's own grade (the bronze plain Repolho)
  function graded(it, nm, grade) {
    const g = grade || GK.data.itemGrade(it);
    return g ? { name: GK.data.stripGrade(nm) || nm, word: t("quality." + g), grade: g } : { name: nm, word: "", grade: null };
  }
  function rowHtml(row, state) {
    const D = GK.data.get(), it = D.items[row.id], nm = name(it, state.overrides);
    let sub;
    if (!row.n) sub = t("rc.raw");
    else {
      // with a station filter on, name that station (it may be an alternative, not the default one)
      const s = V.st && V.st !== "none" && stKey(row.main) !== V.st && IX.stations[V.st] ? IX.stations[V.st] : row.main;
      sub = GK.ui.fmt.buildLabel(s, state.overrides) + (row.n > 1 ? " · " + t("rc.recipes", { n: row.n }) : "");
    }
    const hid = row.hidden ? `<span class="badge badge-hidden">${esc(t(it.unobtainable ? "rc.unobt" : "rc.hidden"))}</span>` : "";
    const g = graded(it, nm);
    return `<button type="button" class="rc-row" id="rc-row-${GK.util.domId(row.id)}" data-open="${esc(row.id)}" aria-label="${esc(t("rc.open", { name: nm }))}">
      ${slot(it, nm)}<span class="rc-row-main"><span class="rc-row-name">${esc(g.name)}${GK.ui.fmt.otherName(it)}${hid}</span><span class="rc-row-sub">${esc(g.word ? g.word + " · " + sub : sub)}</span></span><span class="rc-chev" aria-hidden="true">›</span></button>`;
  }
  function renderMore() {
    const left = results.length - shown;
    moreEl.hidden = left <= 0;
    if (left > 0) moreEl.textContent = t("rc.more", { n: left });
  }
  function updateList(reset) {
    const state = GK.store.get(), D = GK.data.get();
    if (reset) shown = PAGE;
    const c = compute(state);
    results = c.rows;
    chipsEl.innerHTML = chips("cat", c.catN, IX.cats, V.cat, state) + chips("st", c.stN, IX.stations, V.st, state);
    const nOn = (V.cat != null ? 1 : 0) + (V.st != null ? 1 : 0);
    filtersEl.querySelector(".rc-filters-n").textContent = nOn ? t("rc.filtersOn", { n: nOn }) : "";
    const active = [];
    if (V.cat != null) active.push(["cat", name(IX.cats[V.cat] || NOCAT, state.overrides)]);
    if (V.st != null) active.push(["st", name(IX.stations[V.st] || { pt: V.st, en: V.st }, state.overrides)]);
    const hiddenBtn = state.showHidden || c.hiddenN
      ? `<button type="button" class="hidden-toggle" id="rc-hidden" data-rc-hidden aria-pressed="${state.showHidden}">${esc(state.showHidden ? t("rc.hiddenShow") : t("rc.hiddenMore", { n: c.hiddenN }))}</button>` : "";
    metaEl.innerHTML = `<span class="rc-count tabnum" aria-live="polite">${esc(t("rc.count", { n: results.length }))}</span>` +
      active.map(([k, l]) => `<button type="button" class="chip chip-active" data-unfilter="${k}" aria-label="${esc(t("rc.removeFilter", { name: l }))}">${esc(l)} <span aria-hidden="true">×</span></button>`).join("") +
      (active.length > 1 ? `<button type="button" class="btn btn-sm btn-ghost" data-clear-filters>${esc(t("rc.clearFilters"))}</button>` : "");
    hiddenEl.innerHTML = hiddenBtn;   // a power-user switch: at the end of the list, after "Mostrar mais"
    hiddenEl.hidden = !hiddenBtn;
    listEl.innerHTML = results.length ? results.slice(0, shown).map((r) => rowHtml(r, state)).join("")
      : `<p class="rc-empty">${esc(V.q.trim() ? t("rc.noneQ", { q: V.q.trim() }) : t("rc.none"))}</p>`;
    renderMore();
  }
  function showMore() {
    const state = GK.store.get();
    listEl.insertAdjacentHTML("beforeend", results.slice(shown, shown + PAGE).map((r) => rowHtml(r, state)).join(""));
    const first = listEl.children[shown];
    shown += PAGE;
    renderMore();
    if (first) first.focus({ preventScroll: true });
  }
  function staticLabels() {
    input.placeholder = t("rc.placeholder");
    root.querySelector("#rc-q-label").textContent = t("rc.searchLabel");
    clearBtn.setAttribute("aria-label", t("rc.clear"));
    clearBtn.hidden = !input.value;
    root.querySelector(".rc-title").textContent = t("rc.title");
    filtersEl.querySelector(".rc-filters-t").textContent = t("rc.filters");
  }

  /* ---------- detail ---------- */
  const expandable = (r) => r.in.length > 0 && !r.noexp;
  function current(id, state) {
    const D = GK.data.get(), c = state.choice[id] && D.recipeById[state.choice[id]];
    if (c && c.out.item === id) return c;
    const it = D.items[id];
    return it && it.defaultRecipe ? D.recipeById[it.defaultRecipe] || null : null;
  }
  function badges(it, state) {
    const b = [];
    if (edited(it, state.overrides)) b.push(`<span class="badge badge-edited" title="${esc(t("rc.editedTitle"))}">${esc(t("rc.edited"))}</span>`);
    else if (GK.i18n.lang() !== "en" && UNOFFICIAL[it.tr]) b.push(`<span class="badge" title="${esc(t("rc.unofficialTitle"))}">${esc(t("rc.unofficial"))}</span>`);
    if (it.unobtainable) b.push(`<span class="badge badge-warn" title="${esc(t("rc.unobtTitle"))}">${esc(t("rc.unobt"))}</span>`);
    else if (it.hidden) b.push(`<span class="badge badge-hidden" title="${esc(t("rc.hiddenTitle"))}">${esc(t("rc.hidden"))}</span>`);
    return b.join("");
  }
  // "Construir no Cemitério" for a build pseudo-station, the plain name otherwise (corte 12)
  const stationLabel = (s, state) => GK.ui.fmt.buildLabel(s, state.overrides);
  function runes(o) {
    return Object.keys(o || {}).map((k) => `<span class="rune rune-${esc(k)}">${esc(t("rune." + k))} <b>${num(o[k])}</b></span>`).join("");
  }
  // one tappable line: icon, qty, name, note
  // opts.noWord: the grade is picked right below (a group card): no grade word under the name
  function line(l, state, sub, opts) {
    const D = GK.data.get(), it = D.items[l.item], nm = name(it, state.overrides);
    const q = l.qty == null ? "?" : num(l.qty), g = graded(it, nm, l.grade);
    const full = g.grade ? `${g.name} (${g.word})` : nm;
    const word = g.word && !(opts && opts.noWord) ? `<span class="rc-line-note">${esc(g.word)}</span>` : "";
    return `<li><button type="button" class="rc-line"${opts && opts.id ? ` id="${esc(opts.id)}"` : ""} data-open="${esc(l.item)}" aria-label="${esc(q + " × " + full + " · " + t("rc.open", { name: nm }))}">
      ${slot(it, nm, true, l.grade)}<span class="rc-line-q tabnum">${esc(q)}<small>×</small></span>
      <span class="rc-line-main"><span class="rc-line-name">${esc(g.name)}</span>${word}${l.note ? `<span class="rc-line-note">${esc(name(l.note))}</span>` : ""}${sub ? `<span class="rc-line-note">${esc(sub)}</span>` : ""}</span>
      <span class="rc-chev" aria-hidden="true">›</span></button></li>`;
  }
  function itemLine(id, state, sub) {
    const D = GK.data.get(), it = D.items[id], nm = name(it, state.overrides), g = graded(it, nm);
    if (g.word) sub = sub ? g.word + " · " + sub : g.word;
    return `<li><button type="button" class="rc-line" data-open="${esc(id)}" aria-label="${esc(t("rc.open", { name: nm }))}">
      ${slot(it, nm, true)}<span class="rc-line-main"><span class="rc-line-name">${esc(g.name)}${it.hidden ? `<span class="badge badge-hidden">${esc(t(it.unobtainable ? "rc.unobt" : "rc.hidden"))}</span>` : ""}</span>${sub ? `<span class="rc-line-note">${esc(sub)}</span>` : ""}</span>
      <span class="rc-chev" aria-hidden="true">›</span></button></li>`;
  }
  // "Rende 5 com Cozinheiro II" (made_text, exported as out.note; the perk chip lives in the planner's Progresso)
  function yieldLines(r, state) {
    const out = [], b = r.out.bonus;
    if (b && (b.qty != null || b.add != null)) {
      const perk = b.perks.map((p) => name(GK.data.perks()[p] || { en: p })).join(" + ");
      const on = GK.calc.isBonusActive(b, state.perks);
      const txt = b.qty != null ? t("rc.bonusYield", { n: b.qty, perk }) : t("rc.bonusAdd", { n: b.add, perk });
      out.push(`<span class="${on ? "perk-on" : ""}">${esc(txt)}${on ? ` · ✓ ${esc(t("rc.bonusOn"))}` : ""}</span>`);
    } else if (r.out.note) out.push(esc(t("rc.makesNote", { note: name(r.out.note) })));
    if (r.star && (r.star.silver != null || r.star.gold != null)) {
      out.push(esc(t("rc.star", { silver: r.star.silver != null ? r.star.silver : "?", gold: r.star.gold != null ? r.star.gold : "?" })));
    }
    return out;
  }
  function unlockLines(r, noMastery) {
    const out = [];
    if (r.tech) {
      const key = r.tech.type === "quest" ? "rc.quest" : r.tech.type === "perk" ? "rc.perk" : "rc.tech";
      const canLink = r.tech.id && r.tech.type === "technology" && GK.ui.tech && typeof GK.ui.tech.open === "function";
      const tn = esc(name(r.tech));
      const txt = esc(t(key, { tech: "\u0000" })).replace("\u0000", canLink ? `<button type="button" class="rc-link" data-tech="${esc(r.tech.id)}">${tn}</button>` : `<b>${tn}</b>`);
      out.push(txt);
    }
    if (r.mastery && !noMastery) out.push(esc(masteryTxt(r)));
    if (r.ext) out.push(esc(t("rc.ext", { ext: name(r.ext) })));
    if (r.ticks != null) out.push(esc(t("rc.time", { n: r.ticks })));
    if (r.energy != null) out.push(esc(r.ticks != null ? t("rc.energyTotal", { n: r.energy, total: num(r.energy * r.ticks) }) : t("rc.energy", { n: r.energy })));
    return out;
  }
  const masteryTxt = (r) => t("rc.mastery", { type: name(r.mastery.type), level: r.mastery.level ? r.mastery.level : "" }).trim();
  const altNames = (r, state) => r.alt.map((a) => name(a, state.overrides)).join(", ");
  // "Todas também em: Forno da Cozinha II" once above the cards when every recipe (2+) has the same alternatives
  function sharedAlt(rs) {
    if (rs.length < 2 || !rs[0].alt.length) return null;
    const key = (r) => r.alt.map((a) => a.id).sort().join("|"), k0 = key(rs[0]);
    return rs.every((r) => key(r) === k0) ? rs[0] : null;
  }
  // idx: the card's letter ("Receita B"), null = no letter (one card only, or a folded circular one); folded: inside
  // "Melhorar a qualidade" (its title already says circular: no badge)
  function recipeCard(r, idx, it, state, cur, many, altShared, folded) {
    const tags = [];
    if (r.id === it.defaultRecipe) tags.push(`<span class="badge badge-goal">${esc(t("rc.default"))}</span>`);
    if (r.example) tags.push(`<span class="badge badge-ex" title="${esc(t("rc.exampleTitle"))}">${esc(t("rc.example"))}</span>`);
    if (r.noexp) tags.push(`<span class="badge badge-ex">${esc(t("rc.noexp"))}</span>`);
    if (!r.listed) tags.push(`<span class="badge badge-hidden">${esc(t("rc.hiddenRecipe"))}</span>`);
    if (r.cyc && !folded) tags.push(`<span class="badge badge-warn">${esc(t("rc.cyc"))}</span>`);
    const rname = r.name && name(r.name) !== name(it) && (GK.i18n.lang() === "en" || r.name.pt !== r.name.en) ? `<p class="rc-rname">${esc(name(r.name))}</p>` : "";
    const alt = r.alt.length && !altShared ? `<p class="rc-meta-line">${esc(t("rc.alt", { names: altNames(r, state) }))}</p>` : "";
    const ins = r.in.length ? `<ul class="rc-lines">${r.in.map((l) => line(l, state)).join("")}</ul>` : `<p class="rc-meta-line">${esc(t("rc.noInputs"))}</p>`;
    const meta = yieldLines(r, state).concat(unlockLines(r)).map((h) => `<li>${h}</li>`).join("");
    const rn = r.runes ? `<div class="rc-runes"><span class="rc-k">${esc(t("rc.runesNeed"))}</span> ${runes(r.runes)}</div>` : "";
    const extra = r.extra.length ? `<div class="rc-extra"><span class="rc-k">${esc(t("rc.extra"))}</span><ul class="rc-lines">${r.extra.map((l) => line(l, state)).join("")}</ul></div>` : "";
    let act = "";
    if (cur && cur.id === r.id) act = `<span class="rc-inuse">✓ ${esc(t("rc.inUse"))}</span>`;
    else if (expandable(r) && (many || !it.defaultRecipe)) act = `<button type="button" class="btn btn-sm" id="rc-use-${GK.util.domId(r.id)}" data-use="${esc(r.id)}">${esc(t("rc.use"))}</button>`;
    return `<article class="card list rc-recipe">
      ${cardHead(r, idx, state)}
      <div class="rc-recipe-body">
        ${tags.length ? `<div class="rc-tags">${tags.join("")}</div>` : ""}${rname}${alt}${ins}
        ${meta ? `<ul class="rc-meta">${meta}</ul>` : ""}${rn}${extra}
        ${act ? `<div class="rc-act">${act}</div>` : ""}
      </div>
    </article>`;
  }
  function cardHead(r, idx, state) {
    const stName = stationLabel(r.station, state);
    const yieldTxt = r.out.qty == null ? t("rc.makesVar") : t("rc.makes", { n: r.out.qty });
    const letter = idx == null ? "" : `<span class="station-sub">${esc(t("rc.recipeN", { l: String.fromCharCode(65 + (idx % 26)) }))}</span>`;
    return `<header class="station-h">${slot(r.station, stName, true)}<h4>${letter}${esc(stName)}</h4><span class="rc-yield tabnum">${esc(yieldTxt)}</span></header>`;
  }
  // a group card (GK.calc.recipeGroups): the shared lines, then the pick: mode "q" = the grade of one ingredient
  // (bronze / prata / ouro, each with its own amount or mastery when they differ), mode "alt" = "E mais um destes",
  // one row per ingredient with its grades. The option in use is checked; a tap sets it in the planner.
  function groupCard(g, idx, it, state, cur, altShared) {
    const D = GK.data.get(), r0 = g.recipes[0];
    const inUse = g.options.find((o) => cur && o.r.id === cur.id) || null;
    const shown = inUse || g.options[0];
    const pid = (o) => "rc-pick-" + GK.util.domId(o.r.id);
    const word = (o) => (o.grade ? t("quality." + o.grade) : "");
    const baseName = (o) => graded(o.item, name(o.item, state.overrides), o.grade).name;
    const say = (o) => `${num(o.line.qty)}× ${baseName(o)}${o.grade ? " " + word(o) : ""}`;
    const radio = (o, cls, inner, label) => `<button type="button" class="qopt${cls}" role="radio" id="${esc(pid(o))}" data-pick="${esc(o.r.id)}" aria-checked="${o === inUse}"${label ? ` aria-label="${esc(label)}"` : ""}>${inner}</button>`;
    const star = (o) => (o.grade ? `<span class="qstar q-${o.grade[0]}" aria-hidden="true"></span>` : "");
    const hid = "rc-q-" + GK.util.domId(r0.id);
    const fixed = (g.fixed || []).map((l) => line(l, state));
    let pick;
    if (g.mode === "q") {
      fixed.push(line(shown.line, state, "", { noWord: true }));
      const opts = g.options.map((o) => {
        const d = [g.qtyEach ? num(o.line.qty) + "×" : "", g.masteryEach && o.r.mastery ? `${name(o.r.mastery.type)}${o.r.mastery.level ? " " + o.r.mastery.level : ""}` : ""].filter(Boolean).join(" · ");
        return radio(o, "", `<span class="qopt-t">${star(o)}${esc(word(o))}</span>${d ? `<span class="qopt-d">${esc(d)}</span>` : ""}`);
      }).join("");
      pick = `<div class="qpick" role="radiogroup" aria-labelledby="${esc(hid)}"><p class="qpick-h" id="${esc(hid)}">${esc(t("rc.qPick"))}</p>
        <div class="qopts">${opts}</div>`;
    } else {
      const rows = g.rows.map((row) => {
        const nm = name(row.item, state.overrides), bn = graded(row.item, nm).name;
        const os = row.options.map((o) => radio(o, " qopt-sm", `${star(o)}<span class="tabnum">${esc(num(o.line.qty))}×</span>`,
          `${num(o.line.qty)} ${bn}${o.grade ? " (" + word(o) + ")" : ""}`)).join("");
        return `<li><button type="button" class="qalt-it" data-open="${esc(row.item.id)}" aria-label="${esc(t("rc.open", { name: nm }))}">${slot(row.item, nm, true)}<span class="qalt-n">${esc(bn)}</span></button><span class="qalt-o">${os}</span></li>`;
      }).join("");
      pick = `<div class="qpick" role="radiogroup" aria-labelledby="${esc(hid)}"><p class="qpick-h" id="${esc(hid)}">${esc(t("rc.qMore"))}</p>
        <ul class="qalt">${rows}</ul>`;
    }
    const what = inUse ? (g.mode === "q" ? word(inUse) : say(inUse)) : "";
    pick += `<p class="rc-inuse qpick-use" aria-live="polite">${inUse ? `✓ ${esc(t("rc.inUseQ", { what }))}` : ""}</p></div>`;
    const tags = [];
    if (r0.example) tags.push(`<span class="badge badge-ex" title="${esc(t("rc.exampleTitle"))}">${esc(t("rc.example"))}</span>`);
    if (r0.noexp) tags.push(`<span class="badge badge-ex">${esc(t("rc.noexp"))}</span>`);
    if (!r0.listed) tags.push(`<span class="badge badge-hidden">${esc(t("rc.hiddenRecipe"))}</span>`);
    if (r0.cyc) tags.push(`<span class="badge badge-warn">${esc(t("rc.cyc"))}</span>`);
    const alt = r0.alt.length && !altShared ? `<p class="rc-meta-line">${esc(t("rc.alt", { names: altNames(r0, state) }))}</p>` : "";
    const meta = yieldLines(r0, state).concat(unlockLines(r0, g.masteryEach)).map((h) => `<li>${h}</li>`).join("");
    const rn = r0.runes ? `<div class="rc-runes"><span class="rc-k">${esc(t("rc.runesNeed"))}</span> ${runes(r0.runes)}</div>` : "";
    const extra = r0.extra.length ? `<div class="rc-extra"><span class="rc-k">${esc(t("rc.extra"))}</span><ul class="rc-lines">${r0.extra.map((l) => line(l, state)).join("")}</ul></div>` : "";
    return `<article class="card list rc-recipe rc-group">
      ${cardHead(r0, idx, state)}
      <div class="rc-recipe-body">
        ${tags.length ? `<div class="rc-tags">${tags.join("")}</div>` : ""}${alt}${fixed.length ? `<ul class="rc-lines">${fixed.join("")}</ul>` : ""}
        ${pick}
        ${meta ? `<ul class="rc-meta">${meta}</ul>` : ""}${rn}${extra}
      </div>
    </article>`;
  }
  /* ---------- facts: "Onde conseguir", use tooltip, stack (data/facts.json via the build) ---------- */
  const WHERE_CAP = 4, MINUS = "−";
  const signed = (v) => (v < 0 ? MINUS + num(-v) : "+" + num(v));
  const refs = () => (GK.data.get().meta.refs || {});
  const unofficialBadge = (title) => (GK.i18n.lang() !== "en" ? `<span class="badge" title="${esc(title)}">${esc(t("rc.unofficial"))}</span>` : "");
  // a source name: "@item-id" (the app's item name) or a key of meta.refs.names ("x" or {pt, en, tr})
  function refName(ref, state) {
    if (typeof ref !== "string") return { txt: "" };
    if (ref[0] === "@") { const it = GK.data.item(ref.slice(1)); return { txt: it ? name(it, state.overrides) : ref.slice(1), tr: it && UNOFFICIAL[it.tr] }; }
    const e = (refs().names || {})[ref];
    if (e == null) return { txt: ref };
    return typeof e === "string" ? { txt: e } : { txt: name(e), tr: !!e.tr };
  }
  function whereLine(w, state) {
    const k = w[0], nm = refName(w[1], state);
    let what = esc(nm.txt), det = "";
    if (k === "buy") det = w[2] === "talk" ? t("rc.w.talk") : w[2] ? t("rc.w.level", { n: w[2] }) : "";
    else if (k === "fish" && w.length > 2) {
      const bait = w[2] === "no-bait" ? t("rc.w.noBait") : name(GK.data.item(w[2]) || { en: w[2] }, state.overrides);
      what += ", " + esc(bait);
      det = w[3] === w[4] ? t("rc.w.allDay", { d: num(w[3]) }) : t("rc.w.dayNight", { d: num(w[3]), n: num(w[4]) });
    } else if (k === "chest") det = t("rc.w.chestOnce");
    else if (k === "found") det = t("rc.w.once");
    const badge = nm.tr ? unofficialBadge(t("rc.w.unofficialTitle")) : "";
    return `<li><b class="rc-where-v">${esc(t("rc.w." + k))}:</b> ${what}${badge}${det ? ` <span class="rc-where-d">${esc(det)}</span>` : ""}</li>`;
  }
  function whereHtml(it, rs, state) {
    const w = Array.isArray(it.where) ? it.where.filter((x) => Array.isArray(x) && x.length > 1) : [];
    if (!w.length) return "";
    const shown = whereAll ? w : w.slice(0, WHERE_CAP), rest = w.length - shown.length;
    const questOnly = !rs.length && w.every((x) => x[0] === "quest");
    return `<div class="rc-info rc-where"><h3 class="rc-k">${esc(t("rc.where"))}</h3>
      ${questOnly ? `<p class="rc-where-only"><span class="badge badge-warn" title="${esc(t("rc.questOnlyTitle"))}">${esc(t("rc.questOnly"))}</span></p>` : ""}
      <ul class="rc-where-list">${shown.map((x) => whereLine(x, state)).join("")}</ul>
      ${rest > 0 ? `<button type="button" class="btn btn-sm btn-ghost rc-where-more" id="rc-where-more" data-where-more aria-label="${esc(t("rc.whereMoreLabel", { n: rest }))}">${esc(t("rc.whereMore", { n: rest }))}</button>` : ""}
    </div>`;
  }
  function duration(secs) {
    const m = Math.floor(secs / 60), s = secs % 60;
    return [m ? `${num(m)} min` : "", s ? `${num(s)} s` : ""].filter(Boolean).join(" ");
  }
  function buffName(key) {
    const b = (refs().buffs || {})[key];
    return b ? { b, txt: name(b) } : { b: null, txt: key };
  }
  // the game's item tooltip: "Efeito de uso: (bolt) +20", the HUD-like energy bar, the boosted value, the buff
  function tipHtml(it) {
    const u = it.use;
    if (!u || typeof u !== "object") return "";
    const en = typeof u.en === "number" ? u.en : null, ins = typeof u.ins === "number" ? u.ins : null;
    const vals = [];
    if (en != null) vals.push(`<span class="gk-val gk-en"><span class="gk-bolt" role="img" aria-label="${esc(t("rc.energyName"))}"></span>${esc(signed(en))}</span>`);
    if (ins != null) vals.push(`<span class="gk-val gk-ins">${esc(signed(ins))} <small>${esc(t("rc.insanityName"))}</small></span>`);
    const parts = [];
    if (vals.length) parts.push(`<p class="gk-eff"><span class="gk-lbl">${esc(t("rc.useLbl"))}</span> ${vals.join(" ")}</p>`);
    if (en != null && en > 0) {
      const pct = (v) => Math.max(0, Math.min(100, v)) / 100;
      const boost = Array.isArray(u.enB) && typeof u.enB[0] === "number" ? u.enB : null;
      const plus = boost && boost[0] > en ? pct(boost[0]) - pct(en) : 0;
      parts.push(`<div class="gk-bar" role="img" aria-label="${esc(t("rc.barLabel", { n: en }))}">
        <span class="gk-bar-ico"><span class="gk-bolt"></span></span>
        <span class="gk-bar-track"><span class="gk-bar-empty"></span><span class="gk-bar-fill" style="width:calc((100% - 6px) * ${pct(en)})"></span>${plus > 0 ? `<span class="gk-bar-plus" style="left:calc(3px + (100% - 6px) * ${pct(en)});width:calc((100% - 6px) * ${plus.toFixed(3)})"></span>` : ""}<span class="gk-bar-ticks"></span></span>
      </div>`);
    }
    const notes = [];
    if (en != null && en > 0) notes.push(esc(t("rc.bar", { n: en })));
    for (const [f, base] of [["enB", en], ["insB", ins]]) {
      const b = u[f];
      if (!Array.isArray(b) || typeof b[0] !== "number" || base == null) continue;
      const bn = buffName(b[1]);
      notes.push(t("rc.boost", { v: `<b>${esc(f === "enB" ? num(b[0]) : signed(b[0]))}</b>`, buff: `<b${bn.b && bn.b.d ? ` title="${esc(name(bn.b.d))}"` : ""}>${esc(bn.txt)}</b>` }));
    }
    if (notes.length) parts.push(`<p class="gk-note">${notes.join(" · ")}</p>`);
    if (Array.isArray(u.buff) && u.buff.length) {
      const bn = buffName(u.buff[0]), secs = typeof u.buff[1] === "number" ? u.buff[1] : null;
      const d = bn.b && bn.b.d ? name(bn.b.d) : "";
      const time = [secs ? esc(t("rc.lasts", { t: "\u0000" })).replace("\u0000", `<b>${duration(secs)}</b>`) : "", u.buff[2] ? esc(t("rc.restart")) : ""].filter(Boolean).join(" ");
      if (parts.length) parts.push(`<div class="gk-rule" aria-hidden="true"></div>`);
      parts.push(`<div class="gk-buff"><span class="gk-buff-ico" aria-hidden="true"></span><div>
        <p class="gk-buff-name">${esc(bn.txt)}${bn.b && bn.b.tr ? unofficialBadge(t("rc.w.unofficialTitle")) : ""}</p>
        ${d ? `<p class="gk-buff-d">${esc(d)}${bn.b.dtr ? unofficialBadge(t("rc.descUnofficial")) : ""}</p>` : ""}
        ${time ? `<p class="gk-buff-t">${time}</p>` : ""}
      </div></div>`);
    }
    return parts.length ? `<div class="gk-tip">${parts.join("")}</div>` : "";
  }
  // the big item slot with the stack in its corner (as the game prints the count), + one caption line
  function stackSlot(it, nm) {
    const html = slot(it, nm), st = typeof it.stack === "number" && it.stack > 0 ? it.stack : null;
    if (!st || st < 2) return html;
    return html.replace(/^<span class="slot"/, `<span class="slot" title="${esc(t("rc.stackTitle", { n: st }))}"`)
      .replace(/<\/span>$/, `<span class="stack-n tabnum" aria-hidden="true">${esc(num(st))}</span></span>`);
  }
  function stackCap(it) {
    const st = typeof it.stack === "number" && it.stack > 0 ? it.stack : null;
    if (!st) return "";
    return `<p class="stack-cap">${st > 1 ? esc(t("rc.stack", { n: "\u0000" })).replace("\u0000", `<b>${esc(num(st))}</b>`) : esc(t("rc.stackOne"))}</p>`;
  }
  /* ---------- "Quem compra", "Estudar", "Pedido em" (ficha completa) ---------- */
  const int = (v) => (typeof v === "number" && isFinite(v) ? Math.round(v) : 0);
  // an amount in bronze (1 silver = 100 bronze, 1 gold = 100 silver) as the game's coins: (s)1 (b)37
  function coins(v) {
    const parts = [["g", Math.floor(v / 10000)], ["s", Math.floor(v / 100) % 100], ["b", v % 100]].filter((p) => p[1]);
    return parts.map(([k, n]) => `<span class="coin coin-${k}" aria-hidden="true"></span>${esc(num(n))}<span class="sr-only"> ${esc(t("rc.coin." + k))}</span>`).join(" ");
  }
  // lo–hi: one bronze coin when both are under 1 silver ("54–56"), else each amount in full
  function coinRange(lo, hi) {
    if (!hi || hi === lo) return coins(lo);
    if (hi < 100) return `<span class="coin coin-b" aria-hidden="true"></span>${esc(num(lo))}–${esc(num(hi))}<span class="sr-only"> ${esc(t("rc.coin.b"))}</span>`;
    return `${coins(lo)} – ${coins(hi)}`;
  }
  function sellHtml(it, state) {
    const rows = Array.isArray(it.sell) ? it.sell.filter((e) => Array.isArray(e) && typeof e[0] === "string") : [];
    if (!rows.length) return "";
    const base = int(it.price) > 0 ? int(it.price) : 0, fix = !!it.fix && base > 0;
    const li = rows.map((e) => {
      const nm = refName(e[0], state), lo = int(e[1]), hi = int(e[2]), likes = int(e[3]), likeLv = int(e[4]), lvl = int(e[5]);
      let pay = "";
      if (fix) pay = coins(base);
      else if (lo > 0) pay = coinRange(lo, hi) + (base > Math.max(lo, hi) ? ` <span class="sell-max">${esc(t("rc.sellUpTo", { v: "\u0000" })).replace("\u0000", coins(base))}</span>` : "");
      else if (base) pay = `<span class="sell-max">${esc(t("rc.sellUpTo", { v: "\u0000" })).replace("\u0000", coins(base))}</span>`;
      const d = [];
      if (fix) d.push(t("rc.sellFix"));
      if (likes > 0) d.push(likeLv > 1 ? t("rc.sellLikesFrom", { n: num(likes), lv: likeLv }) : t("rc.sellLikes", { n: num(likes) }));
      else if (likes < 0) d.push(likeLv > 1 ? t("rc.sellLikesAnyFrom", { lv: likeLv }) : t("rc.sellLikesAny"));
      if (lvl > 1) d.push(t("rc.sellLevel", { n: lvl }));
      const badge = nm.tr ? unofficialBadge(t("rc.w.unofficialTitle")) : "";
      return `<li><span class="sell-who">${esc(nm.txt)}${badge}</span><span class="sell-pay tabnum">${pay}</span>${d.length ? `<span class="sell-d">${esc(d.join(" · "))}</span>` : ""}</li>`;
    }).join("");
    const note = fix ? esc(t("rc.sellNoteFix", { n: "\u0000" })).replace("\u0000", coins(base)) : esc(t("rc.sellNote"));
    return `<div class="rc-info rc-sell">
      <div class="rc-k-row"><h3 class="rc-k" id="rc-sell-h">${esc(t("rc.sell"))}</h3>
        <details class="rc-i"><summary aria-label="${esc(t("rc.sellInfo"))}" title="${esc(t("rc.sellInfo"))}"><span aria-hidden="true">i</span></summary>
          <p class="rc-i-p">${note}</p></details></div>
      <ul class="sell-list" aria-labelledby="rc-sell-h">${li}</ul>
    </div>`;
  }
  function studyHtml(it, state, id) {
    const st = Array.isArray(it.study) ? it.study.map(int) : [];
    if (!st.length || !st.some((v) => v > 0)) return "";
    const [red, green, blue, sci, faith] = [0, 1, 2, 3, 4].map((i) => st[i] || 0);
    const cost = { red, green, blue };
    // the point gems of "Tecnologias que faltam" (GK.ui.tech.costHtml)
    const pts = (red || green || blue) && GK.ui.tech && GK.ui.tech.costHtml ? GK.ui.tech.costHtml(cost, { big: true }) : "";
    const on = Array.isArray(state.studied) && state.studied.indexOf(id) >= 0;
    const nm = name(it, state.overrides);
    const costTxt = sci || faith ? " " + t(faith ? "rc.studyCostFaith" : "rc.studyCost", { sci: num(sci), faith: num(faith) }) : "";
    return `<div class="rc-info rc-study">
      <h3 class="rc-k">${esc(t("rc.study"))}</h3>
      <div class="study-row">${pts}
        <label class="study-done" for="rc-studied"><span class="tick"><input type="checkbox" id="rc-studied" data-studied="${esc(id)}"${on ? " checked" : ""} aria-label="${esc(t("rc.studiedLabel", { name: nm }))}"></span>${esc(t("rc.studied"))}</label></div>
      <p class="study-d">${esc(t("rc.studyNote") + costTxt)}</p>
    </div>`;
  }
  function askedLine(mark, qty, nameHtml, note) {
    return `<li><div class="rc-line rc-line-static"><span class="slot slot-sm asked-mark"><span class="slot-letter" aria-hidden="true">${mark}</span></span><span class="rc-line-q tabnum">${esc(num(qty))}<small>×</small></span>
      <span class="rc-line-main"><span class="rc-line-name">${nameHtml}</span>${note ? `<span class="rc-line-note">${note}</span>` : ""}</span></div></li>`;
  }
  function askedHtml(it, state) {
    const a = it.asked && typeof it.asked === "object" ? it.asked : {};
    const rows = (k) => (Array.isArray(a[k]) ? a[k].filter((e) => Array.isArray(e) && typeof e[0] === "string") : []);
    const nameOf = (ref) => { const nm = refName(ref, state); return esc(nm.txt) + (nm.tr ? unofficialBadge(t("rc.w.unofficialTitle")) : ""); };
    const q = rows("q"), town = rows("t"), ord = rows("o");
    const other = town.length + ord.length, total = q.length + other;
    if (!total) return "";
    const group = (k) => `<li class="asked-g" aria-hidden="true">${esc(t(k))}</li>`;
    const lines = [];
    if (q.length) {
      lines.push(group("rc.askedQ"));
      for (const e of q) lines.push(askedLine("!", int(e[1]) || 1, nameOf(e[0]), typeof e[2] === "string" ? nameOf(e[2]) : ""));
    }
    if (town.length) {
      lines.push(group("rc.askedTown"));
      for (const e of town) lines.push(askedLine("+", int(e[1]) || 1, nameOf(e[0]), ""));
    }
    if (ord.length) {
      lines.push(group("rc.askedOrder"));
      for (const e of ord) {
        const d = [int(e[2]) > 1 ? t("rc.askedLevel", { n: int(e[2]) }) : "", int(e[3]) > 0 ? t("rc.askedLikes", { n: num(int(e[3])) }) : ""].filter(Boolean);
        lines.push(askedLine("+", int(e[1]) || 1, nameOf(e[0]), esc(d.join(" · "))));
      }
    }
    const show = q.length && other ? t("rc.askedShowQO", { n: q.length, o: other }) : q.length ? t("rc.askedShowQ", { n: q.length }) : t("rc.askedShowO", { n: other });
    return `<section class="rc-sec" aria-labelledby="rc-asked-h">
      <h3 class="h2" id="rc-asked-h">${esc(t("rc.asked"))} <span class="count">${total}</span></h3>
      <details class="card list rc-asked" id="rc-asked"${askedOpen ? " open" : ""}>
        <summary><span class="asked-t"><span class="asked-show">${esc(show)}</span><span class="asked-hide">${esc(t("rc.askedHide"))}</span></span>
          ${q.length ? `<span class="asked-warn">${esc(t("rc.askedWarn"))}</span>` : ""}<span class="rc-chev" aria-hidden="true">›</span></summary>
        <ul class="rc-lines">${lines.join("")}</ul>
      </details>
    </section>`;
  }
  function detailHtml(id, state) {
    const D = GK.data.get(), it = D.items[id], nm = name(it, state.overrides), lang = GK.i18n.lang();
    const other = lang === "en" ? it.pt : it.en;
    const prev = V.stack.length ? D.items[V.stack[V.stack.length - 1]] : null;
    const fromTab = V.from ? GK.router.TABS.find((r) => r.id === V.from) : null;
    const backTxt = prev ? t("rc.backTo", { name: name(prev, state.overrides) }) : fromTab ? t("rc.backTo", { name: t(fromTab.labelKey) }) : t("rc.back");
    const nav = `<nav class="rc-nav">
      <button type="button" class="btn btn-ghost rc-back" id="rc-back" data-back>${esc(backTxt)}</button>
      ${prev || fromTab ? `<button type="button" class="btn btn-sm btn-ghost" id="rc-tolist" data-tolist>${esc(t("rc.toList"))}</button>` : ""}</nav>`;
    const catTxt = [it.cat ? name(it.cat) : "", it.kind !== "item" ? t("rc.kind." + it.kind) : ""].filter(Boolean).join(" · ");
    const g = state.goals.find((x) => x.item === id);
    const goal = `<div class="rc-goal">
      <div class="stepper">
        <button type="button" id="rc-dec" data-qty-d="-1" aria-label="${esc(t("rc.dec"))}">−</button>
        <input id="rc-qty" type="number" inputmode="numeric" min="1" max="999" value="${addQty}" aria-label="${esc(t("rc.qty", { name: nm }))}">
        <button type="button" id="rc-inc" data-qty-d="1" aria-label="${esc(t("rc.inc"))}">+</button>
      </div>
      <button type="button" class="btn rc-add" id="rc-add" data-add-goal>${esc(t("rc.addGoal"))}</button>
      ${g ? `<a class="rc-ingoals" href="#plan">${esc(t("rc.inGoals", { n: g.qty }))} · ${esc(t("rc.toPlan"))}</a>` : ""}
    </div>`;
    const info = [];
    const rs = GK.data.recipesFor(id);
    const where = whereHtml(it, rs, state);
    if (where) info.push(where);
    if (it.obtain && (!rs.length || it.raw || it.unobtainable)) info.push(`<div class="rc-info"><h3 class="rc-k">${esc(t("rc.obtain"))}</h3><p>${esc(name(it.obtain))}</p></div>`);
    if (it.runes) info.push(`<div class="rc-info"><h3 class="rc-k">${esc(t("rc.runes"))}</h3><div class="rc-runes">${runes(it.runes)}</div></div>`);
    const sell = sellHtml(it, state), study = studyHtml(it, state, id);
    if (sell) info.push(sell);
    if (study) info.push(study);
    if (it.members && it.members.length) info.push(`<div class="rc-info"><h3 class="rc-k">${esc(t("rc.members"))}</h3><ul class="rc-lines">${it.members.map((m) => itemLine(m, state)).join("")}</ul></div>`);
    const groups = IX.memberOf[id] || [];
    if (groups.length) info.push(`<div class="rc-info"><h3 class="rc-k">${esc(t("rc.memberOf"))}</h3><ul class="rc-lines">${groups.map((gid) => itemLine(gid, state)).join("")}</ul></div>`);

    const head = `<article class="card rc-item">
      <header class="rc-item-h">${stackSlot(it, nm)}<div class="rc-item-t">
        <h2 class="rc-name" id="rc-detail-h" tabindex="-1">${esc(nm)}</h2>
        ${other && other !== nm ? `<p class="rc-other" lang="${lang === "en" ? "pt-BR" : "en"}">${esc(other)}</p>` : ""}
        ${catTxt ? `<p class="rc-cat">${esc(catTxt)}</p>` : ""}
        ${badges(it, state) ? `<div class="rc-badges">${badges(it, state)}</div>` : ""}
        ${stackCap(it)}
      </div></header>
      ${tipHtml(it)}${goal}${info.join("")}
    </article>`;

    const cur = current(id, state), many = rs.filter(expandable).length > 1;
    const chosen = state.choice[id] && cur && cur.id === state.choice[id] && cur.id !== it.defaultRecipe;
    // grouped cards (GK.calc.recipeGroups); the circular ones folded at the end; a letter only with 2+ cards;
    // "Todas também em" above the cards only with 2+ cards (one card says it inside, as before)
    const G = GK.calc.recipeGroups(rs, D), nCards = G.cards.length;
    const shared = nCards > 1 ? sharedAlt(rs) : null;
    const cards = G.cards.map((c, i) => (c.group ? groupCard(c, nCards > 1 ? i : null, it, state, cur, !!shared)
      : recipeCard(c.r, nCards > 1 ? i : null, it, state, cur, many, !!shared))).join("");
    const cyc = G.cyc.length ? `<details class="rc-cyc" id="rc-cyc"${cycOpen ? " open" : ""}>
        <summary><span class="rc-cyc-t">${esc(t("rc.cycT"))} <span class="count">${G.cyc.length}</span></span><span class="rc-cyc-d">${esc(t("rc.cycD", { name: nm }))}</span><span class="rc-chev" aria-hidden="true">›</span></summary>
        <div class="rc-recipes">${G.cyc.map((r) => recipeCard(r, null, it, state, cur, many, !!shared, true)).join("")}</div>
      </details>` : "";
    // a group with no recipe of its own: its members (in the header card) already say how to get it
    const recipes = !rs.length && it.members ? "" : `<section class="rc-sec" aria-labelledby="rc-recipes-h">
      <div class="section-head"><h3 class="h2" id="rc-recipes-h">${esc(t("rc.recipesTitle"))} <span class="count">${nCards > 1 ? nCards : ""}</span></h3>
        ${chosen ? `<button type="button" class="btn btn-sm btn-ghost" id="rc-use-default" data-use-default>${esc(t("rc.useDefault"))}</button>` : ""}</div>
      ${shared ? `<p class="hint rc-alt-all">${esc(t("rc.altAll", { names: altNames(shared, state) }))}</p>` : ""}
      ${rs.length ? `<div class="rc-recipes">${cards}</div>${cyc}` : `<p class="hint">${esc(t("rc.noRecipes"))}</p>`}
    </section>`;

    // used in: direct consumers, then recipes that take a group this item belongs to
    const used = [];
    const seen = new Map();
    // one row per output + station + amount (eleven "Supplies: Vegetables" recipes collapse into one)
    const push = (r, qty, via) => {
      const k = [r.out.item, r.station.id, qty, via || ""].join("|");
      if (seen.has(k)) { seen.get(k).n++; return; }
      const u = { r, qty, via, n: 1 }; seen.set(k, u); used.push(u);
    };
    for (const r of D.usedIn[id] || []) push(r, r.in.find((l) => l.item === id).qty);
    for (const gid of groups) for (const r of D.usedIn[gid] || []) push(r, r.in.find((l) => l.item === gid).qty, gid);
    const loc = GK.i18n.meta(lang).locale;
    used.sort((a, b) => (D.items[a.r.out.item].hidden - D.items[b.r.out.item].hidden) ||
      name(D.items[a.r.out.item], state.overrides).localeCompare(name(D.items[b.r.out.item], state.overrides), loc));
    GK.data.gradeSort(used, (u) => GK.data.family(D.items[u.r.out.item]), (u) => GK.data.GRADE_RANK[D.items[u.r.out.item].grade]);
    const usedShow = usedAll ? used : used.slice(0, LIST_CAP);
    // nothing uses it: no section at all (corte 18)
    const usedHtml = !used.length ? "" : `<section class="rc-sec" aria-labelledby="rc-used-h">
      <h3 class="h2" id="rc-used-h">${esc(t("rc.usedIn"))} <span class="count">${used.length}</span></h3>
      <div class="card list"><ul class="rc-lines rc-lines-card">${usedShow.map((u) => itemLine(u.r.out.item, state,
        [stationLabel(u.r.station, state), t("rc.uses", { n: u.qty }), u.via ? t("rc.via", { group: name(D.items[u.via], state.overrides) }) : "", u.n > 1 ? t("rc.recipes", { n: u.n }) : ""].filter(Boolean).join(" · "))).join("")}</ul>
        ${used.length > usedShow.length ? `<button type="button" class="btn btn-ghost rc-more" id="rc-used-more" data-used-more>${esc(t("rc.showAll", { n: used.length }))}</button>` : ""}</div>
    </section>`;

    // a station item: what is made there
    let here = "";
    const made = D.stations[id] ? IX.byStation[id] || [] : [];
    if (made.length) {
      const list = hereAll ? made : made.slice(0, LIST_CAP);
      here = `<section class="rc-sec" aria-labelledby="rc-here-h">
        <h3 class="h2" id="rc-here-h">${esc(t("rc.madeHere"))} <span class="count">${made.length}</span></h3>
        <div class="card list"><ul class="rc-lines rc-lines-card">${list.map((r) => itemLine(r.out.item, state,
          r.in.map((l) => `${num(l.qty)} ${name(D.items[l.item], state.overrides)}`).join(" + ") + (r.out.qty ? " → " + num(r.out.qty) : ""))).join("")}</ul>
          ${made.length > list.length ? `<button type="button" class="btn btn-ghost rc-more" id="rc-here-more" data-here-more>${esc(t("rc.showAll", { n: made.length }))}</button>` : ""}</div>
      </section>`;
    }
    return nav + `<div class="rc-detail-grid"><div class="rc-detail-a">${head}</div><div class="rc-detail-b">${recipes}${usedHtml}${askedHtml(it, state)}${here}</div></div>`;
  }
  function renderDetail(state) {
    if (!V.item || !GK.data.item(V.item)) { V.item = null; return false; }
    detailEl.innerHTML = detailHtml(V.item, state);
    return true;
  }

  /* ---------- navigation ---------- */
  const visible = () => GK.router.tab(GK.router.current()).screen === "recipes";
  function showView(state, focusDetail) {
    const hasDetail = V.item && renderDetail(state);
    browseEl.hidden = !!hasDetail;
    detailEl.hidden = !hasDetail;
    if (!hasDetail) { detailEl.innerHTML = ""; updateList(false); }
    if (hasDetail && focusDetail) {
      window.scrollTo(0, 0);
      const h = document.getElementById("rc-detail-h"); if (h) h.focus({ preventScroll: true });
    }
  }
  function openItem(id, fromList) {
    if (!GK.data.item(id)) return;
    if (!IX) buildIndex();
    if (V.item === id) return;
    if (fromList || !V.item) { listScroll = browseEl.hidden ? listScroll : window.scrollY; V.stack = []; V.from = null; }
    else { V.stack.push(V.item); if (V.stack.length > 30) V.stack.shift(); }
    V.item = id; addQty = 1; usedAll = false; hereAll = false; whereAll = false; askedOpen = false; cycOpen = false; cycOpen = false;
    save();
    if (hist) hist.push();
    showView(GK.store.get(), true);
  }
  // back to the screen that opened the detail (GK.ui.recipes.open(id, {from})), where it was
  function backToOrigin() {
    const route = V.from, item = V.item;
    V.item = null; V.stack = []; V.from = null;
    save();
    returnTo = { route, y: fromScroll, item };
    location.hash = route;
  }
  function back(toList) {
    const from = V.item;
    if (!toList && !V.stack.length && V.from) { backToOrigin(); return; }
    if (toList) V.from = null;
    if (!toList && V.stack.length) {
      V.item = V.stack.pop(); addQty = 1; usedAll = false; hereAll = false; whereAll = false; askedOpen = false; cycOpen = false;
      save(); showView(GK.store.get(), true);
      return;
    }
    V.item = null; V.stack = [];
    save();
    showView(GK.store.get(), false);
    window.scrollTo(0, listScroll);
    const row = from && document.getElementById("rc-row-" + GK.util.domId(from));
    if (row) row.focus({ preventScroll: true });
  }
  // deep link from other modules: GK.ui.recipes.open("crate", {from: "plan"})
  function open(itemId, opts) {
    if (!GK.data.item(itemId)) return false;
    if (!IX) buildIndex();
    const cur = GK.router.current();
    const from = opts && opts.from && opts.from !== "recipes" && cur !== "recipes" ? opts.from : null;
    if (from) fromScroll = window.scrollY;
    if (V.item !== itemId || from || V.stack.length) {
      V.stack = []; V.item = itemId; addQty = 1; usedAll = false; hereAll = false; whereAll = false; askedOpen = false; cycOpen = false;
      V.from = from;
      save();
    }
    if (cur !== "recipes") { pendingFocus = true; location.hash = "recipes"; }
    else showView(GK.store.get(), true);
    return true;
  }

  /* ---------- events ---------- */
  function onClick(e) {
    const A = GK.store.actions;
    const el = e.target.closest("button, a");
    if (!el || !root.contains(el)) return;
    const d = el.dataset;
    if (d.open) { openItem(d.open, !!el.closest(".rc-browse")); return; }
    if ("back" in d) { back(false); if (hist) hist.pop(false); return; }
    if ("tolist" in d) { back(true); if (hist) hist.pop(true); return; }
    if (d.chip) {
      const k = d.key, f = d.chip === "cat" ? "cat" : "st";
      V[f] = V[f] === k ? null : k;
      save(); updateList(true);
      const again = chipsEl.querySelector(`[data-chip="${d.chip}"][data-key="${CSS.escape(k)}"]`);
      if (again) again.focus({ preventScroll: true });
      return;
    }
    if (d.chipMore) { expanded[d.chipMore] = !expanded[d.chipMore]; updateList(false); const b = chipsEl.querySelector(`[data-chip-more="${d.chipMore}"]`); if (b) b.focus({ preventScroll: true }); return; }
    if (d.unfilter) { V[d.unfilter] = null; save(); updateList(true); input.focus({ preventScroll: true }); return; }
    if ("clearFilters" in d) { V.cat = null; V.st = null; save(); updateList(true); return; }
    if ("rcHidden" in d) { A.setShowHidden(!GK.store.get().showHidden); const b = document.getElementById("rc-hidden"); if (b) b.focus({ preventScroll: true }); return; }
    if (el === moreEl) { showMore(); return; }
    if (el === clearBtn) { input.value = ""; V.q = ""; save(); clearBtn.hidden = true; updateList(true); input.focus(); return; }
    if (d.qtyD) { const i = document.getElementById("rc-qty"); addQty = GK.store.clampQty((+i.value || 1) + +d.qtyD); i.value = addQty; return; }
    if ("addGoal" in d) {
      const i = document.getElementById("rc-qty"); addQty = GK.store.clampQty(i ? i.value : addQty);
      const s0 = GK.store.get(), before = s0.goals.find((g) => g.item === V.item);
      // the first goal replaces the seeded example: search.js shows one toast with "Desfazer" (meta.exampleReplaced)
      const replacesExample = !!(s0.example && s0.goals.length);
      const n = A.addGoal(V.item, addQty);
      const nm = name(GK.data.item(V.item), GK.store.get().overrides);
      if (!replacesExample) GK.ui.toast(before ? t("rc.bumped", { name: nm, n }) : t("rc.added", { name: nm, n }));
      const b = document.getElementById("rc-add"); if (b) b.focus({ preventScroll: true });
      return;
    }
    if (d.use) {
      const r = GK.data.recipe(d.use); if (!r) return;
      A.chooseRecipe(r.out.item, r.id === GK.data.item(r.out.item).defaultRecipe ? null : r.id);
      GK.ui.toast(t("rc.used", { station: name(r.station, GK.store.get().overrides), name: name(GK.data.item(r.out.item), GK.store.get().overrides) }));
      return;
    }
    // a grade / ingredient option of a group card: the planner uses it from now on (the "✓ Em uso" line says so)
    if (d.pick) {
      const r = GK.data.recipe(d.pick); if (!r || el.getAttribute("aria-checked") === "true") return;
      A.chooseRecipe(r.out.item, r.id === GK.data.item(r.out.item).defaultRecipe ? null : r.id);
      const b = document.getElementById(el.id); if (b) b.focus({ preventScroll: true });
      return;
    }
    if ("useDefault" in d) { A.chooseRecipe(V.item, null); GK.ui.toast(t("rc.usedDefault", { name: name(GK.data.item(V.item), GK.store.get().overrides) })); return; }
    if ("usedMore" in d) { usedAll = true; renderDetail(GK.store.get()); return; }
    if ("hereMore" in d) { hereAll = true; renderDetail(GK.store.get()); return; }
    if ("whereMore" in d) { whereAll = true; renderDetail(GK.store.get()); const l = root.querySelector(".rc-where-list li:nth-child(5)"); if (l) { l.tabIndex = -1; l.focus({ preventScroll: true }); } return; }
    if (d.tech && GK.ui.tech && typeof GK.ui.tech.open === "function") { GK.ui.tech.open(d.tech, { from: "recipes" }); return; }
  }

  function mount(el) {
    root = el;
    root.classList.add("rc-screen");
    root.innerHTML = `<div class="rc-browse">
        <div class="rc-top">
          <h2 class="h2 rc-title"></h2>
          <div class="search-box rc-search">
            <svg width="18" height="18" viewBox="0 0 9 9" aria-hidden="true" shape-rendering="crispEdges"><path fill="currentColor" d="M2 0h3v1H2zM1 1h1v1H1zM5 1h1v1H5zM0 2h1v3H0zM6 2h1v3H6zM1 5h1v1H1zM5 5h1v1H5zM2 6h3v1H2zM6 6h1v1H6zM7 7h1v1H7zM8 8h1v1H8z"/></svg>
            <label class="sr-only" for="rc-q" id="rc-q-label"></label>
            <input id="rc-q" class="search-input" type="search" autocomplete="off" autocapitalize="off" spellcheck="false" enterkeyhint="search">
            <button type="button" class="search-clear" id="rc-q-clear" hidden>×</button>
          </div>
        </div>
        <div class="rc-layout">
          <details class="card rc-filters" id="rc-filters"><summary><span class="rc-filters-t"></span> <span class="rc-filters-n"></span></summary><div class="rc-chips"></div></details>
          <div class="rc-results">
            <div class="rc-meta-row"></div>
            <div class="card list rc-list"></div>
            <button type="button" class="btn rc-more" id="rc-more" hidden></button>
            <div class="rc-hidden-end" hidden></div>
          </div>
        </div>
      </div>
      <div class="rc-detail" hidden></div>`;
    browseEl = root.querySelector(".rc-browse"); detailEl = root.querySelector(".rc-detail");
    input = root.querySelector("#rc-q"); clearBtn = root.querySelector("#rc-q-clear");
    listEl = root.querySelector(".rc-list"); chipsEl = root.querySelector(".rc-chips"); metaEl = root.querySelector(".rc-meta-row");
    moreEl = root.querySelector("#rc-more"); filtersEl = root.querySelector("#rc-filters"); hiddenEl = root.querySelector(".rc-hidden-end");
    restore();
    input.value = V.q;
    // filters open beside the list on wide screens, folded on phones
    const wide = window.matchMedia ? window.matchMedia("(min-width: 900px)") : null;
    if (wide) {
      filtersEl.open = wide.matches;
      const onWide = () => { if (wide.matches) filtersEl.open = true; };
      if (wide.addEventListener) wide.addEventListener("change", onWide); else if (wide.addListener) wide.addListener(onWide);
    }
    const typed = GK.util.debounce(() => { V.q = input.value; saveSoon(); updateList(true); }, 90);
    input.addEventListener("input", () => { clearBtn.hidden = !input.value; typed(); });
    input.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && input.value) { input.value = ""; V.q = ""; save(); clearBtn.hidden = true; updateList(true); }
      else if (e.key === "Enter") { e.preventDefault(); V.q = input.value; save(); updateList(true); input.blur(); }
    });
    root.addEventListener("click", onClick);
    hist = GK.router.detailHistory("recipes", () => { if (V.item && !detailEl.hidden) back(false); });
    // back on the screen that opened the detail: its old scroll position, focus on the opener (after its render)
    GK.router.onChange((id) => {
      if (!returnTo || id !== returnTo.route) { if (id !== "recipes") returnTo = null; return; }
      const r = returnTo; returnTo = null;
      setTimeout(() => {
        window.scrollTo(0, r.y);
        const scr = document.querySelector(`[data-screen="${GK.router.tab(r.route).screen}"]`);
        const b = scr && r.item && scr.querySelector(`[data-recipe-open="${CSS.escape(r.item)}"]`);
        if (b) b.focus({ preventScroll: true });
      }, 0);
    });
    root.addEventListener("input", (e) => {
      if (e.target.id === "rc-qty" && e.target.value !== "") addQty = GK.store.clampQty(e.target.value);
    });
    root.addEventListener("change", (e) => {
      if (e.target.id === "rc-qty") { addQty = GK.store.clampQty(e.target.value); e.target.value = addQty; }
      // "Já estudei": the store re-renders the detail; the box gets the focus back
      if (e.target.id === "rc-studied" && e.target.dataset.studied) {
        GK.store.actions.setStudied(e.target.dataset.studied, e.target.checked);
        const b = document.getElementById("rc-studied"); if (b) b.focus({ preventScroll: true });
      }
    });
    // "Pedido em" stays open across re-renders of the same item (toggle does not bubble: capture)
    root.addEventListener("toggle", (e) => { if (e.target.id === "rc-asked") askedOpen = e.target.open; if (e.target.id === "rc-cyc") cycOpen = e.target.open; }, true);
    // the price "i": one open at a time; a tap anywhere else closes it
    document.addEventListener("click", (e) => {
      if (!root) return;
      root.querySelectorAll("details.rc-i[open]").forEach((d) => { if (!d.contains(e.target)) d.open = false; });
    });
    root.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && e.target.id === "rc-qty") { e.preventDefault(); const b = document.getElementById("rc-add"); if (b) b.click(); }
      // the grade options: the arrows move between them (a radio group); Enter / Space picks
      const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key];
      if (step && e.target.getAttribute && e.target.getAttribute("role") === "radio" && e.target.closest(".qpick")) {
        const all = [...e.target.closest(".qpick").querySelectorAll('[role="radio"]')], i = all.indexOf(e.target);
        const next = all[(i + step + all.length) % all.length];
        if (next) { e.preventDefault(); next.focus(); }
      }
    });
  }
  let wasHere = false;
  function render(state, meta) {
    const here = visible();
    if (!here) { wasHere = false; return; }
    if (!IX) buildIndex();
    staticLabels();
    const entering = !wasHere;
    wasHere = true;
    showView(state, false);
    // entering: an open detail starts at its top; the list is where GK.router left it (its per-screen scroll memory)
    if (entering && meta && meta.from === "router" && V.item) window.scrollTo(0, 0);
    if (pendingFocus) {
      pendingFocus = false;
      const h = V.item && document.getElementById("rc-detail-h");
      if (h) h.focus({ preventScroll: true });
    }
  }
  return { mount, render, open };
})();

GK.router.register({ id: "recipes", labelKey: "rc.tab", screen: "recipes", order: 20, tab: true });
GK.app.registerPanel(GK.ui.recipes, { id: "recipes", panel: "recipes", order: 62 });
