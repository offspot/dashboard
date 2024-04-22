// matches polyfill
this.Element && function(ElementPrototype) {
    ElementPrototype.matches = ElementPrototype.matches ||
    ElementPrototype.matchesSelector ||
    ElementPrototype.webkitMatchesSelector ||
    ElementPrototype.msMatchesSelector ||
    function(selector) {
        var node = this, nodes = (node.parentNode || node.document).querySelectorAll(selector), i = -1;
        while (nodes[++i] && nodes[i] != node);
        return !!nodes[i];
    }
}(Element.prototype);
// closest polyfill
this.Element && function(ElementPrototype) {
    ElementPrototype.closest = ElementPrototype.closest ||
    function(selector) {
        var el = this;
        while (el.matches && !el.matches(selector)) el = el.parentNode;
        return el.matches ? el : null;
    }
}(Element.prototype);

// helper for enabling IE 8 event bindings
function addEvent(el, type, handler) {
    if (el.attachEvent) el.attachEvent('on'+type, handler); else el.addEventListener(type, handler);
}

function hasClass(el, className) {
  return el.classList ? el.classList.contains(className) : new RegExp('\\b'+ className+'\\b').test(el.className);
}

function addClass(el, className) {
  if (el.classList) el.classList.add(className);
  else if (!hasClass(el, className)) el.className += ' ' + className;
}

function removeClass(el, className) {
  if (el.classList) el.classList.remove(className);
  else el.className = el.className.replace(new RegExp('\\b'+ className+'\\b', 'g'), '');
}

function toggleClass(el, className) {
  if (hasClass(el, className))
    removeClass(el, className);
  else
    addClass(el, className);
}

// live binding helper using matchesSelector
function live(selector, event, callback, context) {
    addEvent(context || document, event, function(e) {
        var found, el = e.target || e.srcElement;
        while (el && el.matches && el !== context && !(found = el.matches(selector))) el = el.parentElement;
        if (found) callback.call(undefined, el, e);
    });
}

function getCookie(name) {
  var v = document.cookie.match('(^|;) ?' + name + '=([^;]*)(;|$)');
  return v ? v[2] : null;
}

function setCookie(name, value, deleteAfter) {
  document.cookie = name + '=' + value + ';path=/;max-age=' + deleteAfter;
}

function deleteCookie(name) { setCookie(name, '', -1); }

const Filtering = class {
  order_by = 'name';
  order_dir = 'desc';
  only_lang = '';
  only_category = '';

  constructor(order_by, order_dir, only_lang, only_category) {
    this.order_by = order_by || this.order_by;
    this.order_dir = order_dir || this.order_dir;
    this.only_lang = only_lang || this.only_lang;
    this.only_category = only_category || this.only_category;
  }

  toString() {
    return `order_by=${this.order_by}, order_dir=${this.order_dir}, only_lang=${this.only_lang}, only_category=${this.only_category}`
  }

  sortByNameAsc(a, b) {
    a = a.getAttribute('data-name').toLowerCase();
    b = b.getAttribute('data-name').toLowerCase();
    if (a == b)
      return 0;
    return a > b ? -1 : 1;
  }

  sortByNameDesc(a, b) {
    a = a.getAttribute('data-name').toLowerCase();
    b = b.getAttribute('data-name').toLowerCase();
    if (a == b)
      return 0;
    return a < b ? -1 : 1;
  }

  sortBySizeAsc(a, b) {
    a = parseInt(a.getAttribute('data-size'));
    b = parseInt(b.getAttribute('data-size'));
    if (a == b)
      return 0;
    return a < b ? -1 : 1;
  }

  sortBySizeDesc(a, b) {
    a = parseInt(a.getAttribute('data-size'));
    b = parseInt(b.getAttribute('data-size'));
    if (a == b)
      return 0;
    return a > b ? -1 : 1;
  }

  sortByDOMOrder(a, b) {
    return 0;
  }

  getSortFunction() {
    if (this.order_by == 'name')
      return (this.order_dir == 'asc') ? this.sortByNameAsc : this.sortByNameDesc;
    if (this.order_by == 'size')
      return (this.order_dir == 'asc') ? this.sortBySizeAsc : this.sortBySizeDesc;
    return this.sortByDOMOrder;
  }

  render(withSorting) {
    const elems = document.getElementById('entries').getElementsByClassName('hotspot-entry');
    for (var i=0; i<elems.length; i++) {
      const langs = elems[i].getAttribute('data-langs').split(' ');
      const category = elems[i].getAttribute('data-category');
      var visible = true;
      if (this.only_lang && langs.indexOf(this.only_lang) == -1)
        visible = false;
      if (visible && this.only_category && this.only_category != category)
        visible = false;

      if (visible)
        removeClass(elems[i], 'hidden');
      else
        addClass(elems[i], 'hidden');
    }

    if (!withSorting)
      return;


    const sortedElems = [].slice.call(elems).toSorted(this.getSortFunction());
    for (var i=0; i<elems.length; i++) {
      elems[i].style.order = sortedElems.indexOf(elems[i]);
    }
  };
};

function run() {
  var page = document.querySelector('body').getAttribute('data-page');

  if (page == "home") {
    live('.hotspot-entry', 'click', function(el, ev){
      ev.preventDefault();
      ev.stopPropagation();
      let target = '';
      if (hasClass(el, 'hotspot-entry')) {
        target = el.getAttribute('data-target');
      } else { // should not happen
        let entryEl = el.closest('.hotspot-entry');
        target = entryEl.getAttribute('data-target');
      }
      window.location.assign(target);
    });
  }

  var filter = new Filtering();

  live('#languages-list', 'change', function(el, ev){
    if (filter.only_lang == el.value)
      return;
    filter.only_lang = el.value;
    filter.render();
  });
  live('#categories-list', 'change', function(el, ev){
    filter.only_category = el.value;
    filter.render();
  });

  function onSortByButtonClick (el, ev) {
    if (filter.order_by == el.value)
      return;
    const btns = document.getElementsByClassName('kiwix-sort-btn');
    for (var i=0; i<btns.length; i++) {
      if (btns[i] == el) {
        addClass(btns[i], 'kiwix-sort-btn-active');
        addClass(btns[i], `kiwix-${page}-btn-active`);
      } else {
        removeClass(btns[i], 'kiwix-sort-btn-active');
        removeClass(btns[i], `kiwix-${page}-btn-active`);
      }
    }
    filter.order_by = el.value;
    filter.render(true);
  }
  function onOrderDirButtonClick (el, ev) {
    if (filter.order_dir == el.value)
      return;
    const btns = document.getElementsByClassName('kiwix-order-dir-btn');
    for (var i=0; i<btns.length; i++) {
      toggleClass(btns[i], `kiwix-${page}-btn-active`);
    }
    filter.order_dir = el.value;
    filter.render(true);
  }

  function onCloseDownloadDrawerButtonClick(el, ev) {
    // go to home (from downloads)
    window.location.assign("/");
  }

  function onOpenDownloadDrawerButtonClick(el, ev) {
    // go (back) to downloads (from home)
    window.location.assign("/download");
  }

  live('#sort-by-name', 'click', onSortByButtonClick);
  live('#sort-by-natural', 'click', onSortByButtonClick);
  live('#sort-by-size', 'click', onSortByButtonClick);
  live('#order-desc', 'click', onOrderDirButtonClick);
  live('#order-asc', 'click', onOrderDirButtonClick);

  live('#close-download-drawer', 'click', onCloseDownloadDrawerButtonClick);
  live('#open-download-drawer', 'click', onOpenDownloadDrawerButtonClick);

  filter.render(true);
}

if (document.readyState!='loading') run(); // already loaded
else if (document.addEventListener) document.addEventListener('DOMContentLoaded', run); // modern browsers
else document.attachEvent('onreadystatechange', function() { if (document.readyState=='complete') run();}); // IE <= 8
