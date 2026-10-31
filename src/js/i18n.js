/* GK.i18n: languages, the merged dictionary and text lookup.
   Owns: LANGS, DICT (filled by each module through GK.i18n.add), the current language.
   Exposes: GK.i18n.{add, t, name, edited, num, set, detect, lang, meta, LANGS, DICT}.
   t(key, {n}) picks key.one / key.other (Intl.PluralRules; 0 uses .other); missing keys fall back to pt.
   Add a language: a LANGS entry, its strings in every module's add() call, and data built with --lang xx=...
*/
GK.i18n = (function () {
  const LANGS = [
    { code: "pt", locale: "pt-BR", label: "PT", name: "Português" },
    { code: "en", locale: "en", label: "EN", name: "English" },
  ];
  // Each module merges its own strings: GK.i18n.add({ pt: {...}, en: {...} }) at the top of its file.
  const DICT = {};
  LANGS.forEach((l) => { DICT[l.code] = {}; });
  function add(dicts) {
    for (const [code, entries] of Object.entries(dicts || {})) Object.assign(DICT[code] || (DICT[code] = {}), entries);
  }
  let lang = "pt", fmt = new Intl.NumberFormat("pt-BR"), rules = new Intl.PluralRules("pt-BR");
  const meta = (code) => LANGS.find((l) => l.code === code) || LANGS[0];
  function detect() {
    const n = String((navigator.languages && navigator.languages[0]) || navigator.language || "").toLowerCase();
    return n.startsWith("en") ? "en" : "pt";
  }
  function set(code) {
    lang = DICT[code] ? code : "pt";
    const m = meta(lang);
    fmt = new Intl.NumberFormat(m.locale);
    rules = new Intl.PluralRules(m.locale);
    document.documentElement.lang = m.locale;
    return lang;
  }
  const num = (n) => fmt.format(n);
  // t("key", {n, ...}) — `n` picks key.one / key.other via Intl.PluralRules (0 always uses .other).
  function t(key, vars) {
    const d = DICT[lang], base = DICT.pt;
    let s;
    if (vars && typeof vars.n === "number") {
      const cat = vars.n === 0 ? "other" : rules.select(vars.n);
      s = d[key + "." + cat] || d[key + ".other"] || base[key + "." + cat];
    }
    if (s == null) s = d[key] != null ? d[key] : base[key] != null ? base[key] : key;
    if (!vars) return s;
    return s.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? (typeof vars[k] === "number" ? num(vars[k]) : vars[k]) : m));
  }
  // Localized name for anything with {pt, en, …}. overrides = state.overrides ({lang: {id: name}}).
  function name(obj, overrides) {
    if (!obj) return "";
    if (obj.i18n) return t(obj.i18n);
    const o = overrides && overrides[lang];
    if (o && obj.id && o[obj.id]) return o[obj.id];
    return obj[lang] || obj.en || obj.pt || obj.id || "";
  }
  const edited = (obj, overrides) => !!(obj && obj.id && overrides && overrides[lang] && overrides[lang][obj.id]);
  return { LANGS, DICT, add, detect, set, t, name, edited, num, lang: () => lang, meta };
})();
