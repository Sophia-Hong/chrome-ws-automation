// Content script — executes DOM commands in the page context

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  const { command, params } = message;

  try {
    let result;

    switch (command) {
      case "click":
        result = handleClick(params);
        break;
      case "fill":
        result = handleFill(params);
        break;
      case "getText":
        result = handleGetText(params);
        break;
      case "getLinks":
        result = handleGetLinks(params);
        break;
      case "evaluate":
        result = handleEvaluate(params);
        break;
      case "snapshot":
        result = handleSnapshot(params);
        break;
      case "querySelector":
        result = handleQuerySelector(params);
        break;
      case "scroll":
        result = handleScroll(params);
        break;
      case "waitForSelector":
        handleWaitForSelector(params).then(sendResponse);
        return true; // async
      default:
        result = { error: `Unknown command: ${command}` };
    }

    sendResponse(result);
  } catch (err) {
    sendResponse({ error: err.message });
  }
});

function findElement(selector) {
  const el = document.querySelector(selector);
  if (!el) throw new Error(`Element not found: ${selector}`);
  return el;
}

function handleClick(params) {
  const el = findElement(params.selector);
  el.click();
  return { clicked: params.selector };
}

function handleFill(params) {
  const el = findElement(params.selector);
  el.focus();
  el.value = params.value;
  el.dispatchEvent(new Event("input", { bubbles: true }));
  el.dispatchEvent(new Event("change", { bubbles: true }));
  return { filled: params.selector, value: params.value };
}

function handleGetText(params) {
  if (params.selector) {
    const el = findElement(params.selector);
    return { text: el.innerText };
  }
  return { text: document.body.innerText.slice(0, 50000) };
}

function handleGetLinks(params) {
  const anchors = Array.from(document.querySelectorAll("a[href]"));
  const links = anchors.map((a) => ({
    text: a.innerText.trim().slice(0, 200),
    href: a.href,
  }));
  if (params && params.filter) {
    const re = new RegExp(params.filter, "i");
    return { links: links.filter((l) => re.test(l.text) || re.test(l.href)) };
  }
  return { links: links.slice(0, 500) };
}

function handleEvaluate(params) {
  // WARNING: executes arbitrary JS in page context
  const fn = new Function(params.expression);
  const result = fn();
  return { result: result };
}

function handleSnapshot(params) {
  const snapshot = {
    url: window.location.href,
    title: document.title,
    meta: {},
    headings: [],
    forms: [],
    links_count: document.querySelectorAll("a").length,
  };

  // Meta tags
  document.querySelectorAll("meta[name], meta[property]").forEach((m) => {
    const key = m.getAttribute("name") || m.getAttribute("property");
    snapshot.meta[key] = m.getAttribute("content");
  });

  // Headings
  document.querySelectorAll("h1, h2, h3").forEach((h) => {
    snapshot.headings.push({
      level: h.tagName,
      text: h.innerText.trim().slice(0, 200),
    });
  });

  // Forms
  document.querySelectorAll("form").forEach((f) => {
    const inputs = Array.from(f.querySelectorAll("input, textarea, select")).map(
      (i) => ({
        type: i.type || i.tagName.toLowerCase(),
        name: i.name,
        id: i.id,
        placeholder: i.placeholder,
      })
    );
    snapshot.forms.push({ action: f.action, method: f.method, inputs });
  });

  // Visible text excerpt
  if (!params || !params.noText) {
    snapshot.text = document.body.innerText.slice(0, 10000);
  }

  return snapshot;
}

function handleQuerySelector(params) {
  const elements = Array.from(document.querySelectorAll(params.selector));
  return {
    count: elements.length,
    elements: elements.slice(0, 100).map((el) => ({
      tag: el.tagName.toLowerCase(),
      id: el.id,
      class: el.className,
      text: el.innerText?.trim().slice(0, 200),
      href: el.href,
    })),
  };
}

function handleScroll(params) {
  if (params.selector) {
    const el = findElement(params.selector);
    el.scrollIntoView({ behavior: "smooth" });
  } else {
    window.scrollBy(0, params.y || 500);
  }
  return { scrolled: true };
}

async function handleWaitForSelector(params) {
  const timeout = params.timeout || 10000;
  const start = Date.now();
  while (Date.now() - start < timeout) {
    if (document.querySelector(params.selector)) {
      return { found: true, selector: params.selector };
    }
    await new Promise((r) => setTimeout(r, 200));
  }
  return { found: false, selector: params.selector, timeout: true };
}
