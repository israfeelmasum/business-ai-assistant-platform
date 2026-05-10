/**
 * Chatbot Widget v2.1 — Action-Oriented, Microservices Enabled, Boss Approved (Pre-Chat Lead Form with Glassmorphism)
 */
(function () {
  'use strict';

  if (typeof window.marked === 'undefined') {
    var script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/marked/marked.min.js';
    document.head.appendChild(script);
  }

  var s = document.currentScript || document.querySelector('script[data-api-key]');
  var C = {
    key: s?.getAttribute('data-api-key') || '',
    url: s?.getAttribute('data-api-url') || (window.location.origin + '/api/v1'),
    pos: s?.getAttribute('data-position') || 'bottom-right',
    thm: s?.getAttribute('data-theme') || '#5A67D8',
    wel: s?.getAttribute('data-welcome') || 'Hello! Welcome to ICT Bangladesh. How can I assist you today?',
    ttl: s?.getAttribute('data-title') || 'AI Assistant',
    sub: s?.getAttribute('data-subtitle') || 'Online',
  };
  if (!C.key) return;

  var open = false, isMin = false, loading = false, selCat = null,
      lang = 'en-US', voice = true, pendingImg = null, recording = false;
  var sid = 'sess_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8);
  var msgs = [], cats = [];
  var SIDE = C.pos.includes('right') ? 'right' : 'left';
  var NS = 'cw' + Math.random().toString(36).slice(2, 6);
  var preChatFilled = false; // Step 1: Pre-chat form data

  var SVG = {
    x:       '<svg viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
    min:     '<svg viewBox="0 0 24 24"><line x1="5" y1="12" x2="19" y2="12"/></svg>',
    max:     '<svg viewBox="0 0 24 24"><polyline points="15 3 21 3 21 9"></polyline><polyline points="9 21 3 21 3 15"></polyline><line x1="21" y1="3" x2="14" y2="10"></line><line x1="3" y1="21" x2="10" y2="14"></line></svg>',
    send:    '<svg viewBox="0 0 24 24"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>',
    newchat: '<svg viewBox="0 0 24 24"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>',
    mic:     '<svg viewBox="0 0 24 24"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>',
    play:    '<svg viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>',
    stop:    '<svg viewBox="0 0 24 24"><rect x="6" y="6" width="12" height="12"></rect></svg>',
    attach:  '<svg viewBox="0 0 24 24"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>',
    dots:    '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="2"/><circle cx="19" cy="12" r="2"/><circle cx="5" cy="12" r="2"/></svg>',
    like:    '<svg viewBox="0 0 24 24"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path></svg>',
    dislike: '<svg viewBox="0 0 24 24"><path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h3a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-3"></path></svg>',
    human:   '<svg viewBox="0 0 24 24"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>'
  };

  var styleEl = document.createElement('style');
  styleEl.textContent = `
    #${NS}-R, #${NS}-R * { box-sizing: border-box; margin: 0; border: 0; }
    #${NS}-R { font-family: 'Plus Jakarta Sans', -apple-system, sans-serif; font-size: 14px; color: #1E293B; }

    #${NS}-F { position: fixed; bottom: 24px; ${SIDE}: 24px; background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.5); box-shadow: 0 4px 12px rgba(0,0,0,0.08); cursor: pointer; z-index: 2147483646; display: flex; align-items: center; gap: 8px; padding: 10px 14px; border-radius: 30px; transition: 0.2s; }
    #${NS}-F:hover { background: rgba(255, 255, 255, 0.9); }
    #${NS}-F.h { opacity: 0; pointer-events: none; }
    .${NS}f-icon { width: 34px; height: 34px; }
    .${NS}f-text { font-weight: 700; font-size: 16px; color: #1E293B; }

    /* 🚀 GLASSMORPHISM MAIN PANEL */
    #${NS}-P { position: fixed; bottom: 90px; ${SIDE}: 24px; width: 380px; height: min(600px, calc(100vh - 112px)); background: rgba(255, 255, 255, 0.25); backdrop-filter: blur(25px); -webkit-backdrop-filter: blur(25px); border-radius: 16px; box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.15); z-index: 2147483647; display: flex; flex-direction: column; overflow: hidden; opacity: 0; transform: translateY(16px) scale(0.96); pointer-events: none; transition: 0.3s; border: 1px solid rgba(255, 255, 255, 0.4); }
    #${NS}-P.o { opacity: 1; transform: translateY(0) scale(1); pointer-events: auto; }
    #${NS}-P.min { height: auto; width: 320px; }

    /* Transparent Headers & Areas */
    .${NS}hd { background: transparent; color: #1E293B; padding: 14px 16px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(255, 255, 255, 0.3); }
    .${NS}hl { display: flex; align-items: center; gap: 10px; }
    .${NS}av { width: 32px; height: 32px; background: transparent; border-radius: 50%; }
    .${NS}ht { font-weight: 700; font-size: 15px; line-height: 1.2; color: #1E293B;}
    .${NS}hs { font-size: 11px; display: flex; align-items: center; gap: 5px; color: #334155; font-weight: 500; }
    .${NS}dot { width: 6px; height: 6px; border-radius: 50%; background: #10B981; box-shadow: 0 0 4px rgba(16,185,129,0.5); }
    .${NS}hr { display: flex; gap: 6px; align-items: center; }

    .${NS}hb { background: transparent; color: #475569; cursor: pointer; padding: 6px; border-radius: 6px; transition: 0.2s; display: flex;}
    .${NS}hb:hover { background: rgba(255, 255, 255, 0.4); color: #1E293B; }
    .${NS}hb svg { width: 16px; height: 16px; stroke: currentColor; fill: none; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }

    .${NS}lb { font-size: 10px; font-weight: 700; padding: 4px 8px; border-radius: 12px; background: rgba(255, 255, 255, 0.4); color: #475569; cursor: pointer; border: 1px solid rgba(255, 255, 255, 0.5); transition: 0.2s;}
    .${NS}lb:hover { background: rgba(255, 255, 255, 0.6); color: #1E293B; }

    .${NS}cs { display: flex; gap: 8px; padding: 10px 14px; overflow-x: auto; background: transparent; border-bottom: 1px solid rgba(255, 255, 255, 0.3); }
    .${NS}cs::-webkit-scrollbar { height: 0; }
    .${NS}cb { padding: 6px 14px; border-radius: 20px; border: 1px solid transparent; background: transparent; color: #475569; font-size: 13px; font-weight: 600; cursor: pointer; white-space: nowrap; transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1); }
    .${NS}cb:hover { color: #1E293B; background: rgba(255, 255, 255, 0.3); }
    .${NS}cb.a { font-weight: 700; color: #1E293B; transform: scale(1.05); background: rgba(255, 255, 255, 0.5); border-color: rgba(255, 255, 255, 0.6); box-shadow: 0 2px 5px rgba(0,0,0,0.05);}

    .${NS}ms { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 18px; background: transparent; }
    .${NS}rw { display: flex; align-items: flex-end; gap: 8px; }
    .${NS}rw.u { justify-content: flex-end; }
    .${NS}rw.b { justify-content: flex-start; }

    .${NS}bb { padding: 12px 16px; font-size: 13.5px; line-height: 1.5; max-width: 85%; word-break: break-word; backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); }

    /* Glass Bubbles */
    .${NS}bb.u { background: rgba(248, 250, 252, 0.6); color: #1E293B; border-radius: 16px 16px 4px 16px; border: 1px solid rgba(255, 255, 255, 0.5); }
    .${NS}bb.b { background: rgba(255, 255, 255, 0.65); color: #1E293B; border-radius: 16px 16px 16px 4px; border: 1px solid rgba(255, 255, 255, 0.6); box-shadow: 0 4px 15px rgba(0,0,0,0.03); }

    .${NS}bb img { max-width: 100%; border-radius: 8px; margin-bottom: 5px; }

    .${NS}td { display: flex; gap: 4px; align-items: center; }
    .${NS}td span { width: 6px; height: 6px; border-radius: 50%; background: ${C.thm}; animation: ${NS}bdt 1.4s infinite ease-in-out both; }
    .${NS}td span:nth-child(1) { animation-delay: -0.32s; }
    .${NS}td span:nth-child(2) { animation-delay: -0.16s; }
    @keyframes ${NS}bdt { 0%, 80%, 100% { transform: scale(0); } 40% { transform: scale(1); } }
    .${NS}rw.b .${NS}bb.${NS}t-ind { background: transparent; border: none; box-shadow: none; padding: 6px 4px; backdrop-filter: none; }

    .${NS}bb p { margin-bottom: 8px; }
    .${NS}bb p:last-child { margin-bottom: 0; }

    /* Glass Input Area */
    .${NS}ia { padding: 12px 16px 16px 16px; background: transparent; border-top: none; }
    .${NS}iw { border: 1px solid rgba(255, 255, 255, 0.6); border-radius: 16px; background: rgba(255, 255, 255, 0.5); backdrop-filter: blur(15px); -webkit-backdrop-filter: blur(15px); padding: 12px 12px 46px 12px; display: flex; flex-direction: column; transition: border-color 0.2s, box-shadow 0.2s; position: relative; box-shadow: 0 4px 15px rgba(0,0,0,0.03); }
    .${NS}iw:focus-within { border-color: rgba(255, 255, 255, 0.9); box-shadow: 0 4px 15px rgba(0,0,0,0.06); }

    .${NS}pv { display: none; position: relative; width: 60px; height: 60px; margin-bottom: 8px; }
    .${NS}pv img { width: 100%; height: 100%; object-fit: cover; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.5); }
    .${NS}px { position: absolute; top: -6px; right: -6px; background: #EF4444; color: #fff; border-radius: 50%; width: 16px; height: 16px; font-size: 10px; cursor: pointer; display: flex; align-items: center; justify-content: center; }

    .${NS}in { width: 100%; border: none; outline: none; resize: none; font-size: 14px; font-family: inherit; color: #1E293B; background: transparent; padding: 0; min-height: 24px; max-height: 120px; line-height: 1.5; }
    .${NS}in::placeholder { color: #64748B; font-weight: 500; }

    .${NS}ic { display: flex; gap: 6px; align-items: center; position: absolute; bottom: 10px; right: 12px; }

    .${NS}send { background: ${C.thm}; color: #fff; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; cursor: pointer; border: none; transition: 0.2s; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
    .${NS}send:hover { transform: scale(1.05); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
    .${NS}send:disabled { opacity: 0.4; cursor: default; transform: none; background: #94A3B8; box-shadow: none; }
    .${NS}send svg { width: 14px; height: 14px; stroke: currentColor; fill: none; stroke-width: 2.5; stroke-linecap: round; stroke-linejoin: round; transform: translate(-1px, 1px); }

    .${NS}ibtn { background: rgba(255, 255, 255, 0.6); color: #475569; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; cursor: pointer; border: 1px solid rgba(255, 255, 255, 0.5); transition: 0.2s; }
    .${NS}ibtn:hover { background: rgba(255, 255, 255, 0.9); color: ${C.thm}; }
    .${NS}ibtn svg { width: 14px; height: 14px; stroke: currentColor; fill: none; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
    .${NS}ibtn.rec { color: #EF4444; animation: ${NS}pulse 1.5s infinite; border-color: rgba(239, 68, 68, 0.3); }
    
    .${NS}tts { background: transparent; border: none; color: #64748B; cursor: pointer; padding: 6px; border-radius: 50%; display: flex; align-items: center; justify-content: center; transition: 0.2s; margin-left: 2px; }
    .${NS}tts:hover { color: ${C.thm}; background: rgba(255, 255, 255, 0.5); }
    .${NS}tts svg { width: 14px; height: 14px; fill: currentColor; }

    @keyframes ${NS}pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.5; transform: scale(1.1); } }
  `;
  document.head.appendChild(styleEl);

  var root = document.createElement('div');
  root.id = NS + '-R';
  document.body.appendChild(root);

  var fab = document.createElement('div');
  fab.id = NS + '-F';
  fab.innerHTML = '<img src="./unnamed-removebg-preview.png" class="'+NS+'f-icon" alt="Bulb"><span class="'+NS+'f-text">Ask AI</span>';
  fab.onclick = toggle;
  root.appendChild(fab);

  var pnl = document.createElement('div');
  pnl.id = NS + '-P';
  pnl.innerHTML = `
    <div class="${NS}hd">
      <div class="${NS}hl">
        <img src="./unnamed-removebg-preview.png" class="${NS}av" alt="Logo">
        <div>
          <div class="${NS}ht">${esc(C.ttl)}</div>
          <div class="${NS}hs"><span class="${NS}dot"></span>${esc(C.sub)}</div>
        </div>
      </div>
      <div class="${NS}hr">
        <button class="${NS}hb" id="${NS}-new" title="New Chat">${SVG.newchat}</button>
        <button class="${NS}lb" id="${NS}-lng" title="Select Bangla">🇺🇸 EN</button>
        <button class="${NS}hb" id="${NS}-min" title="Minimize">${SVG.min}</button>
        <button class="${NS}hb" id="${NS}-cls" title="Close">${SVG.x}</button>
      </div>
    </div>
    <div class="${NS}cs" id="${NS}-cs" style="display:flex;"></div>
    <div class="${NS}ms" id="${NS}-ms"></div>

    <div class="${NS}ia" id="${NS}-ia">
      <div class="${NS}iw">
        <div class="${NS}pv" id="${NS}-pv">
            <img id="${NS}-pvi" src="">
            <button class="${NS}px" id="${NS}-px">✕</button>
        </div>
        <textarea class="${NS}in" id="${NS}-in" placeholder="Ask me anything..." rows="1"></textarea>

        <input type="file" id="${NS}-file" accept="image/png, image/jpeg, image/jpg, image/webp" style="display:none;">

        <div class="${NS}ic">
            <button class="${NS}ibtn" id="${NS}-att" title="Upload Image">${SVG.attach}</button>
            
            <button class="${NS}ibtn" id="${NS}-mic" title="Voice Input">${SVG.mic}</button>
            <button class="${NS}send" id="${NS}-sb" disabled title="Send Message">${SVG.send}</button>
        </div>
      </div>
    </div>
  `;
  root.appendChild(pnl);

  var dom = {
    ms: ge(NS + '-ms'), in: ge(NS + '-in'), sb: ge(NS + '-sb'), cs: ge(NS + '-cs'),
    lng: ge(NS + '-lng'),
    pv: ge(NS + '-pv'), pvi: ge(NS + '-pvi'), px: ge(NS + '-px'), mic: ge(NS + '-mic'),
    ia: ge(NS + '-ia'),
    file: ge(NS + '-file'), att: ge(NS + '-att')
  };

  ge(NS + '-cls').onclick = toggle;
  ge(NS + '-min').onclick = function() {
    isMin = !isMin;
    pnl.classList.toggle('min', isMin);
    ge(NS + '-min').innerHTML = isMin ? SVG.max : SVG.min;
    ge(NS + '-min').title = isMin ? "Expand" : "Minimize";
    dom.cs.style.display = isMin ? 'none' : 'flex';
    dom.ms.style.display = isMin ? 'none' : 'flex';
    dom.ia.style.display = isMin ? 'none' : 'block';
  };

  ge(NS + '-new').onclick = function() {
    sid = 'sess_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8);
    msgs = []; pendingImg = null; hidePreview(); dom.in.value = ''; resetHeight();
    lastProcessedIndex = 0;
    addMsg('bot', C.wel);
    autoPlayLastMsg();
  };

  dom.lng.onclick = function() {
    lang = lang === 'en-US' ? 'bn-BD' : 'en-US';
    dom.lng.innerHTML = lang === 'en-US' ? '🇺🇸 EN' : '🇧🇩 BN';
    dom.lng.title = lang === 'en-US' ? 'Select Bangla' : 'Select English';
    dom.in.placeholder = lang === 'en-US' ? 'Ask me anything...' : 'কিছু জিজ্ঞাসা করুন...';
  };

  dom.in.addEventListener('input', function() {
    resetHeight();
    dom.sb.disabled = (!this.value.trim() && !pendingImg);
  });

  dom.in.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  });

  dom.att.onclick = function() {
    dom.file.click();
  };

  dom.file.onchange = function(e) {
    var file = e.target.files[0];
    if (!file) return;
    
    if(file.size > 5 * 1024 * 1024) {
        alert("File is too large. Please upload an image smaller than 5MB.");
        dom.file.value = '';
        return;
    }

    var reader = new FileReader();
    reader.onload = function(ev) {
      pendingImg = ev.target.result;
      dom.pvi.src = pendingImg;
      dom.pv.style.display = 'block';
      dom.sb.disabled = false;
      dom.in.focus();
    };
    reader.readAsDataURL(file);
  };

  dom.px.onclick = function() {
    pendingImg = null;
    dom.file.value = '';
    dom.pv.style.display = 'none';
    dom.sb.disabled = !dom.in.value.trim();
  };

  dom.mic.onclick = function() {
    if('webkitSpeechRecognition' in window) {
      var rec = new window.webkitSpeechRecognition();
      rec.continuous = false; rec.interimResults = false; rec.lang = lang;
      rec.onstart = function() { recording = true; dom.mic.classList.add('rec'); };
      rec.onresult = function(e) {
          dom.in.value += (dom.in.value ? ' ' : '') + e.results[0][0].transcript;
          resetHeight(); dom.sb.disabled = false;
      };
      rec.onerror = function() { recording = false; dom.mic.classList.remove('rec'); dom.in.focus(); };
      rec.onend = function() { recording = false; dom.mic.classList.remove('rec'); dom.in.focus(); };
      rec.start();
    } else { alert("Voice input not supported in this browser."); }
  };

  dom.sb.onclick = send;

  // ==========================================
  // 🚀 LAISA'S TTS ENGINE (Auto-Play & Play/Stop Logic)
  // ==========================================
  var synth = window.speechSynthesis;
  var currentSpokenBtn = null;

  function playTTSVoice(btn, textToSpeak) {
      if (synth.speaking && currentSpokenBtn === btn) {
          synth.cancel();
          btn.innerHTML = SVG.play;
          currentSpokenBtn = null;
          return;
      }
      synth.cancel();
      if (currentSpokenBtn) currentSpokenBtn.innerHTML = SVG.play;

      var cleanText = textToSpeak.replace(/<[^>]*>?/gm, '').replace(/\*/g, '');
      var utterance = new SpeechSynthesisUtterance(cleanText);
      utterance.lang = lang;
      
      utterance.onend = function() {
          if(currentSpokenBtn === btn) { btn.innerHTML = SVG.play; currentSpokenBtn = null; }
      };
      utterance.onerror = utterance.onend;

      btn.innerHTML = SVG.stop;
      currentSpokenBtn = btn;
      synth.speak(utterance);
  }

  function autoPlayLastMsg() {
      setTimeout(function() {
          var btns = dom.ms.querySelectorAll('.' + NS + 'tts');
          if (btns.length > 0) {
              var lastBtn = btns[btns.length - 1];
              playTTSVoice(lastBtn, lastBtn.getAttribute('data-text'));
          }
      }, 300);
  }

  dom.ms.addEventListener('click', function(e) {
      var btn = e.target.closest('.' + NS + 'tts');
      if (!btn) return;
      playTTSVoice(btn, btn.getAttribute('data-text'));
  });

  function ge(id) { return document.getElementById(id); }
  function esc(t) { var d = document.createElement('div'); d.textContent = t; return d.innerHTML; }
  function resetHeight() {
    dom.in.style.height = 'auto';
    dom.in.style.height = Math.min(dom.in.scrollHeight, 120) + 'px';
  }
  
  function hidePreview() { 
    pendingImg = null; 
    dom.pv.style.display = 'none'; 
    dom.sb.disabled = !dom.in.value.trim(); 
    if(dom.file) dom.file.value = ''; 
  }

  function addMsg(role, content, img, isTyping = false) {
    msgs.push({ r: role, c: content, img: img, isTyping: isTyping });
    draw();
  }

  function updLast(content) {
    for (var i = msgs.length - 1; i >= 0; i--) {
      if (msgs[i].r === 'bot' && !msgs[i].isTyping) { msgs[i].c = content; break; }
    }
    draw();
  }

  function parseText(txt) {
    if(typeof window.marked !== 'undefined') return window.marked.parse(txt);
    return esc(txt).replace(/\n/g, '<br>');
  }

  function draw() {
    dom.ms.innerHTML = msgs.map(function (m) {
      if (m.isTyping) {
          return '<div class="'+NS+'rw b"><img src="./unnamed-removebg-preview.png" class="'+NS+'av" style="align-self:flex-end;width:28px;height:28px;animation:'+NS+'pulse 1s infinite;"><div class="'+NS+'bb b '+NS+'t-ind" style="display:flex; align-items:center;"><div class="'+NS+'td"><span></span><span></span><span></span></div></div></div>';
      }

      var html = m.img ? '<img src="'+m.img+'">' : '';
      html += m.c ? parseText(m.c) : '';

      if (m.r === 'user') {
        return '<div class="'+NS+'rw u"><div class="'+NS+'bb u">' + html + '</div></div>';
      }
      
      var safeText = m.c ? m.c.replace(/"/g, '&quot;').replace(/'/g, '&#39;') : '';
      var ttsBtn = m.c ? '<button class="'+NS+'tts" data-text="'+safeText+'" title="Read Aloud">'+SVG.play+'</button>' : '';

      return '<div class="'+NS+'rw b"><img src="./unnamed-removebg-preview.png" class="'+NS+'av" style="align-self:flex-end;width:28px;height:28px;"><div style="display:flex; align-items:flex-end;"> <div class="'+NS+'bb b">' + html + '</div>' + ttsBtn + '</div></div>';
    }).join('');
    dom.ms.scrollTop = dom.ms.scrollHeight;
  }

  async function loadCats() {
    try {
      var res = await fetch(C.url + '/entities/types', { headers: { 'x-api-key': C.key } });
      if (res.ok) cats = await res.json();
    } catch (e) { console.log("API offline. Loading fallback categories."); }

    if (!cats || cats.length === 0) {
        cats = [
            { name: 'course', display_name: 'Courses' },
            { name: 'faq', display_name: 'Faqs' },
            { name: 'General_Datas', display_name: 'About us' }
        ];
    }

    var html = '<button class="'+NS+'cb a" data-v="">All</button>';
    cats.forEach(function (cat) {
      var label = (cat.name === 'General_Datas' || cat.display_name === 'General_Datas') ? 'About us' : (cat.display_name || cat.name);
      html += '<button class="'+NS+'cb" data-v="'+esc(cat.name)+'">'+esc(label)+'</button>';
    });
    dom.cs.innerHTML = html;

    dom.cs.querySelectorAll('.'+NS+'cb').forEach(function(b) {
      b.onclick = function() {
        dom.cs.querySelectorAll('.'+NS+'cb').forEach(function(x){ x.classList.remove('a'); });
        b.classList.add('a');
        selCat = b.dataset.v || null;
      };
    });
  }

  async function send() {
    var text = dom.in.value.trim();
    if ((!text && !pendingImg) || loading) return;

    var imgToSend = pendingImg;
    addMsg('user', text, imgToSend);
    dom.in.value = ''; resetHeight(); hidePreview();

    loading = true; dom.sb.disabled = true;
    addMsg('bot', '', null, true);

    var sysMsg = text;
    if (!sysMsg && imgToSend) {
        sysMsg = "Here is the screenshot of my payment proof. Please analyze it.";
    }
    
    if(lang === 'bn-BD' && sysMsg) {
        sysMsg += " [SYSTEM: Reply natively in Bengali.]";
    }

    var chatHistory = msgs.filter(m => !m.isTyping && m.c).map(m => ({
        role: m.r === 'bot' ? 'assistant' : 'user',
        content: m.c
    })).slice(-10);

    try {
      var res = await fetch(C.url + '/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-api-key': C.key },
        body: JSON.stringify({ 
            message: sysMsg, 
            messages: chatHistory, 
            session_id: sid, 
            entity_type: selCat, 
            image_base64: imgToSend, 
            stream: true 
        }),
      });

      var reader = res.body.getReader();
      var decoder = new TextDecoder('utf-8');
      var fullText = '';
      var isFirst = true;

      while (true) {
        var result = await reader.read();
        if (result.done) break;

        var chunk = decoder.decode(result.value, { stream: true });
        var lines = chunk.split('\n');

        for (var i = 0; i < lines.length; i++) {
          if (!lines[i].startsWith('data: ')) continue;
          var raw = lines[i].slice(6).trim();
          if (raw === '[DONE]') continue;
          try {
            var parsed = JSON.parse(raw);
            if (parsed.content) {
              fullText += parsed.content;
              var dText = fullText;

              if(dText.includes('<think>')) dText = dText.replace(/<think>[\s\S]*?(<\/think>|$)/gi, '').trim();

              if(dText !== '') {
                if(isFirst) {
                    msgs = msgs.filter(m => !m.isTyping);
                    addMsg('bot', dText);
                    isFirst = false;
                } else {
                    updLast(dText);
                }
              }
            }
          } catch (e) {}
        }
      }
      if (isFirst && !fullText) {
          msgs = msgs.filter(m => !m.isTyping);
          draw();
      } else if (fullText) {
          autoPlayLastMsg(); 
      }
    } catch (err) {
      msgs = msgs.filter(m => !m.isTyping);
      addMsg('bot', '⚠️ Connection Error.');
    }
    loading = false; dom.sb.disabled = false; dom.in.focus();
  }
  
  var pollInterval = null;
  var lastProcessedIndex = 0;

  async function checkAgentReplies() {
    if (!open || !sid) return;

    try {
      var res = await fetch(C.url + '/chat/history/' + sid, { 
          headers: { 'x-api-key': C.key } 
      });
      
      if (!res.ok) return;
      var data = await res.json();
      var serverMsgs = data.messages || [];
      
      if (serverMsgs.length > lastProcessedIndex) {
          var newMsgs = serverMsgs.slice(lastProcessedIndex);
          
          newMsgs.forEach(msg => {
              if (msg.role === 'agent') {
                  addMsg('bot', msg.content);
              }
              else if (msg.role === 'assistant' && msg.content !== '' && msgs.length > 0) {
                 var alreadyExists = msgs.some(m => m.c === msg.content);
                 if (!alreadyExists) {
                     addMsg('bot', msg.content);
                 }
              }
          });
          
          lastProcessedIndex = serverMsgs.length;
          autoPlayLastMsg(); 
      }
    } catch (e) {}
  }

  function toggle() {
    open = !open;
    pnl.classList.toggle('o', open);
    fab.classList.toggle('h', open);
    
    if (open && msgs.length === 0) {
        loadCats();
        addMsg('bot', C.wel);
        autoPlayLastMsg(); 
    }
    
    if (open) {
        setTimeout(function () { if(!isMin) dom.in.focus(); }, 300);
        
        if (!pollInterval) {
            pollInterval = setInterval(checkAgentReplies, 5000); 
        }
    } else {
        if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
        }
        if (synth.speaking) {
            synth.cancel();
            if (currentSpokenBtn) currentSpokenBtn.innerHTML = SVG.play;
            currentSpokenBtn = null;
        }
    }
  }
})();