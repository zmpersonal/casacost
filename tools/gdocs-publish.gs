/**
 * CasaCost — "Publish to CasaCost" for Google Docs
 * ------------------------------------------------------------------
 * Gives you a custom menu INSIDE Google Docs. Write a post in the Doc,
 * click Publish, fill in slug / meta / tags, and it commits a Markdown
 * file to your GitHub repo — which triggers the GitHub Actions build and
 * the post goes live on casacost.com. This IS the "write in a Doc, click,
 * published" workflow. The menu lives in Docs (Docs can run code; a static
 * site can't), but functionally it's exactly that.
 *
 * ONE-TIME SETUP
 * 1. Open your Google Doc → Extensions → Apps Script.
 * 2. Delete any sample code, paste this whole file, Save.
 * 3. Edit the CONFIG below (repo owner, repo name, branch, posts folder).
 * 4. Create a GitHub fine-grained Personal Access Token with
 *    "Contents: Read and write" on just this repo. Copy it.
 * 5. In Apps Script: Project Settings → Script Properties →
 *    add property  GITHUB_TOKEN  = <your token>.  (Keeps it out of the code.)
 * 6. Reload the Doc. You'll see a "CasaCost" menu. Click Publish.
 *
 * Writing tips: use the Doc's Heading 2 / Heading 3 styles for section
 * headings and normal paragraphs for body — they convert to Markdown.
 */

var CONFIG = {
  owner:  "YOUR_GITHUB_USERNAME",
  repo:   "casacost",
  branch: "main",
  folder: "content/blog",       // where posts live in the repo
  author: "CasaCost"
};

function onOpen() {
  DocumentApp.getUi()
    .createMenu("CasaCost")
    .addItem("Publish to CasaCost…", "showPublishDialog")
    .addToMenu();
}

function showPublishDialog() {
  var doc = DocumentApp.getActiveDocument();
  var suggestedTitle = doc.getName();
  var suggestedSlug = slugify(suggestedTitle);
  var today = Utilities.formatDate(new Date(), "UTC", "yyyy-MM-dd");
  var html = HtmlService.createHtmlOutput(
    '<style>body{font-family:Arial;font-size:13px;margin:0}label{display:block;margin:10px 0 3px;font-weight:bold}' +
    'input,textarea{width:100%;box-sizing:border-box;padding:7px;border:1px solid #ccc;border-radius:6px}' +
    'button{margin-top:14px;padding:9px 16px;background:#1E3D2E;color:#fff;border:0;border-radius:7px;cursor:pointer}</style>' +
    '<label>Title</label><input id="title" value="' + escapeHtml(suggestedTitle) + '">' +
    '<label>Slug (URL)</label><input id="slug" value="' + escapeHtml(suggestedSlug) + '">' +
    '<label>Meta title (optional)</label><input id="metatitle" placeholder="SEO &lt;title&gt;">' +
    '<label>Meta description</label><textarea id="desc" rows="2" maxlength="160"></textarea>' +
    '<label>Date</label><input id="date" value="' + today + '">' +
    '<label>Tags (comma-separated)</label><input id="tags" placeholder="pool, austin, pricing">' +
    '<button onclick="go()">Publish to GitHub</button>' +
    '<p id="status" style="color:#2F5F45"></p>' +
    '<script>function go(){document.getElementById("status").textContent="Publishing…";' +
    'var p={title:title.value,slug:slug.value,metatitle:metatitle.value,desc:desc.value,date:date.value,tags:tags.value};' +
    'google.script.run.withSuccessHandler(function(m){document.getElementById("status").textContent=m;})' +
    '.withFailureHandler(function(e){document.getElementById("status").textContent="Error: "+e.message;})' +
    '.publishToGitHub(p);}</script>'
  ).setWidth(420).setHeight(430);
  DocumentApp.getUi().showModalDialog(html, "Publish to CasaCost");
}

function publishToGitHub(p) {
  var token = PropertiesService.getScriptProperties().getProperty("GITHUB_TOKEN");
  if (!token) throw new Error("No GITHUB_TOKEN in Script Properties.");

  var slug = p.slug || slugify(p.title);
  var body = docToMarkdown();
  var fm = "---\n" +
    "title: " + p.title + "\n" +
    "slug: " + slug + "\n" +
    (p.metatitle ? "meta_title: " + p.metatitle + "\n" : "") +
    "description: " + (p.desc || "") + "\n" +
    "date: " + (p.date || Utilities.formatDate(new Date(), "UTC", "yyyy-MM-dd")) + "\n" +
    "author: " + CONFIG.author + "\n" +
    (p.tags ? "tags: " + p.tags + "\n" : "") +
    "---\n\n" + body + "\n";

  var path = CONFIG.folder + "/" + (p.date || "") + "-" + slug + ".md";
  var apiUrl = "https://api.github.com/repos/" + CONFIG.owner + "/" + CONFIG.repo + "/contents/" + path;

  // check if file exists (need its SHA to update)
  var sha = null;
  var check = UrlFetchApp.fetch(apiUrl + "?ref=" + CONFIG.branch, {
    method: "get", muteHttpExceptions: true,
    headers: { Authorization: "Bearer " + token, Accept: "application/vnd.github+json" }
  });
  if (check.getResponseCode() === 200) sha = JSON.parse(check.getContentText()).sha;

  var payload = {
    message: "Publish post: " + p.title,
    content: Utilities.base64Encode(fm, Utilities.Charset.UTF_8),
    branch: CONFIG.branch
  };
  if (sha) payload.sha = sha;

  var res = UrlFetchApp.fetch(apiUrl, {
    method: "put", contentType: "application/json", muteHttpExceptions: true,
    headers: { Authorization: "Bearer " + token, Accept: "application/vnd.github+json" },
    payload: JSON.stringify(payload)
  });
  var code = res.getResponseCode();
  if (code === 200 || code === 201)
    return "Published ✓  The site will rebuild in ~1 minute at casacost.com/blog/" + slug + "/";
  throw new Error("GitHub " + code + ": " + res.getContentText());
}

/** Minimal Google Doc -> Markdown (headings, bold, lists, paragraphs). */
function docToMarkdown() {
  var body = DocumentApp.getActiveDocument().getBody();
  var out = [];
  for (var i = 0; i < body.getNumChildren(); i++) {
    var el = body.getChild(i);
    var type = el.getType();
    if (type === DocumentApp.ElementType.PARAGRAPH) {
      var para = el.asParagraph();
      var text = para.getText();
      if (!text.trim()) { out.push(""); continue; }
      var h = para.getHeading();
      if (h === DocumentApp.ParagraphHeading.HEADING1) out.push("# " + text);
      else if (h === DocumentApp.ParagraphHeading.HEADING2) out.push("## " + text);
      else if (h === DocumentApp.ParagraphHeading.HEADING3) out.push("### " + text);
      else out.push(inlineMarkdown(para));
    } else if (type === DocumentApp.ElementType.LIST_ITEM) {
      var li = el.asListItem();
      var glyph = li.getGlyphType();
      var bullet = (glyph === DocumentApp.GlyphType.NUMBER) ? "1. " : "- ";
      out.push(bullet + li.getText());
    }
  }
  return out.join("\n\n").replace(/\n{3,}/g, "\n\n");
}

function inlineMarkdown(para) {
  var text = para.getText();
  var t = para.editAsText();
  var result = "", n = text.length;
  for (var i = 0; i < n; i++) {
    var ch = text[i];
    var bold = t.isBold(i);
    var prevBold = i > 0 ? t.isBold(i - 1) : false;
    if (bold && !prevBold) result += "**";
    result += ch;
    var nextBold = i < n - 1 ? t.isBold(i + 1) : false;
    if (bold && !nextBold) result += "**";
  }
  return result;
}

function slugify(s) {
  return String(s).toLowerCase().replace(/['"]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
}
function escapeHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
