import re, sys, shutil
PATH = sys.argv[1] if len(sys.argv) > 1 else 'index.html'
src = open(PATH, encoding='utf-8').read()
if 'V63' in src and 'captureReferral' in src:
    print('This file already looks patched (V63). Nothing to do.'); sys.exit(0)
s = src
def must(cond, msg):
    if not cond: print("ANCHOR MISSING:", msg); sys.exit(1)
def rep(old, new, count=1, label=None):
    global s
    must(old in s, label or old[:70])
    s = s.replace(old, new, count)

# ---------- version label ----------
s = s.replace('V62', 'V63')

# ---------- viewport ----------
rep('<meta name="viewport" content="width=device-width, initial-scale=1.0" />',
    '<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />')

# ---------- CSS: zoom only on desktop + mobile fixes ----------
rep('''    body { zoom: 0.8; }
    @supports not (zoom: 0.8) {
      body { transform: scale(0.8); transform-origin: top center; width: 125%; }
    }''', '''    @media (min-width: 769px) { body { zoom: 0.8; } }''', label='zoom block')

MOBILE_CSS = '''
    /* ===== V63 mobile fixes ===== */
    html, body { overflow-x: hidden; }
    .container { padding-bottom: calc(130px + env(safe-area-inset-bottom, 0px)); }
    .bottom-nav { padding-bottom: calc(14px + env(safe-area-inset-bottom, 0px)); }
    .nav-item { min-width: 56px; min-height: 44px; }
    input, select, textarea { font-size: 16px; }
    .table { display: block; overflow-x: auto; white-space: nowrap; -webkit-overflow-scrolling: touch; }
    @media (max-width: 768px) {
      .container { padding-left: 14px; padding-right: 14px; padding-top: 14px; }
      .stat-row, .stat-row[style] { grid-template-columns: 1fr !important; }
      [style*="grid-template-columns:repeat(4"] { grid-template-columns: 1fr 1fr !important; }
      [style*="grid-template-columns:repeat(3"] { grid-template-columns: 1fr 1fr !important; }
      [style*="grid-template-columns:1fr 1fr;gap:24px"] { grid-template-columns: 1fr !important; }
      .stat-value { font-size: 1.35rem; }
      .page-title { font-size: 1.35rem; }
      .hero { padding: 16px; }
      .hero-btns { flex-wrap: wrap; }
      .hero-btns button { flex: 1; }
      .modal { padding: 12px; align-items: flex-end; }
      .modal-inner { padding: 20px; max-height: 88vh; overflow-y: auto; border-radius: 16px 16px 12px 12px; }
      .topbar-inner { padding: 0 14px; }
      .btn-connect { padding: 9px 12px; font-size: 0.85rem; }
      #accountMenu { left: 12px !important; right: 12px !important; min-width: 0 !important; }
    }
'''
rep('  </style>', MOBILE_CSS + '  </style>', label='</style>')

# ---------- ABI additions ----------
rep('        "function fund(uint256 amountU)",', '        "function fund(uint256 amountU)",\n        "function getBcfRequired(uint256 purchaseId) view returns (uint256)",')
rep('        "function getUSDTPoolBalance() view returns (uint256)",\n      ],',
    '        "function getUSDTPoolBalance() view returns (uint256)",\n        "function getRedeemPrice() view returns (uint256)",\n        "function getBuyPrice() view returns (uint256)",\n        "function getCredit(address) view returns (uint256)",\n      ],', label='Operations ABI')
rep('        "function buyNode(uint256) returns (uint256)",', '        "function buyNode(uint256) returns (uint256)",\n        "function buyNodeWithCredit(uint256,uint256) returns (uint256)",')
rep('        "function getUserInfo(address) view returns (uint256,uint256,uint256,uint256)",',
    '        "function getUserInfo(address) view returns (uint256,uint256,uint256,uint256)",\n        "function users(address) view returns (address,uint256,uint256,uint256,uint8,uint256,uint256,bool)",', label='Referral ABI')

# ---------- Owner panel -> admin link ----------
pat = re.compile(r"\n\s*\$\{state\.account && state\.account\.toLowerCase\(\) === MOCK_USDT_OWNER\.toLowerCase\(\) && state\.deployed \? `.*?` : ''\}\n(?=      `;\n    \}\n\n    function renderInsurance)", re.S)
must(pat.search(s), 'owner panel markup')
s = pat.sub('''
        ${state.account && state.account.toLowerCase() === MOCK_USDT_OWNER.toLowerCase() ? `
          <div class="notice notice-info" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
            <span>🛠 You are connected as the contract owner.</span>
            <a class="btn-purchase" href="/admin.html" style="position:static;text-decoration:none;display:inline-block;">Open Admin Panel →</a>
          </div>
        ` : ''}
''', s, count=1)

a = s.index('      // Owner — Mint 10,000 USDT (test)')
b = s.index('      // Dashboard — Copy Address')
s = s[:a] + s[b:]

rep('Owner must fund Insurance pool first. Use "Mint 10,000 USDT" then fund insurance (Owner Panel on Dashboard).',
    'The admin funds the Insurance pool from the Admin page. Claiming also requires returning the BCF you received at purchase.')

# ---------- menu: admin link ----------
rep("""          <button class='btn-gold' onclick='location.hash="#/network"'>Network</button>
        </div>""", """          <button class='btn-gold' onclick='location.hash="#/network"'>Network</button>
          ${state.account && state.account.toLowerCase() === MOCK_USDT_OWNER.toLowerCase() ? "<button class='btn-gold' onclick='location.href=\\"/admin.html\\"'>🛠 Admin Panel</button>" : ""}
        </div>""", label='menu')

# ---------- #1 Redeem (8.4 fee) ----------
rep('''            <div style="display:flex;justify-content:space-between;padding-top:6px;border-top:1px solid var(--border);font-size:0.75rem;color:var(--muted);">
              <span>Slippage: 5% (minimum output)</span>
            </div>''', '''            <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
              <span style="color:var(--muted);">Redeem fee (10%):</span>
              <span style="color:var(--red);" id="redeemFee">—</span>
            </div>
            <div style="padding-top:6px;border-top:1px solid var(--border);font-size:0.75rem;color:var(--muted);">
              Fee = 4% paid in USDT + 6% paid in BCF · Slippage 5% (minimum output)
            </div>''', label='redeem slippage block')

a = s.index('    async function updateRedeemEstimate() {')
b = s.index('\n    }\n', a) + 7
NEW_EST = '''    // Redeem price + fee model. New Operations (8.4) exposes getRedeemPrice() and charges 10%;
    // an older Operations without it falls back to the oracle price with no fee.
    async function getRedeemQuote() {
      try {
        const p = await getContract("Operations").getRedeemPrice();
        return { price: Number(ethers.formatUnits(p, 18)), netFactor: 0.9, hasFee: true };
      } catch (e) {}
      try {
        const p = await getContract("PriceOracle").getPrice();
        return { price: Number(ethers.formatUnits(p, 18)), netFactor: 1, hasFee: false };
      } catch (e) {}
      return { price: 0, netFactor: 1, hasFee: false };
    }

    async function updateRedeemEstimate() {
      const bcfInp = document.getElementById("redeemBcfAmount");
      const receiveEl = document.getElementById("redeemReceive");
      const priceEl = document.getElementById("redeemPrice");
      const rateEl = document.getElementById("redeemRate");
      const feeEl = document.getElementById("redeemFee");
      if (!bcfInp || !receiveEl) return;
      const amt = Number(bcfInp.value || 0);
      try {
        const q = await getRedeemQuote();
        if (priceEl) priceEl.textContent = "$" + q.price.toFixed(4);
        if (rateEl) rateEl.textContent = "$" + q.price.toFixed(4);
        const gross = amt * q.price;
        const net = gross * q.netFactor;
        receiveEl.textContent = (amt > 0 ? net : 0).toFixed(4) + " USDT";
        if (feeEl) feeEl.textContent = q.hasFee ? ((amt > 0 ? gross - net : 0).toFixed(4) + " USDT-equiv") : "none";
      } catch (e) {
        console.error("updateRedeemEstimate error:", e);
      }
    }
'''
s = s[:a] + NEW_EST + s[b:]

pat = re.compile(r"          // Get current price for minUsdtOut\n.*?const minUsdtOut = ethers\.parseUnits\(\(expectedUsdt \* 0\.95\)\.toFixed\(2\), 18\);\n", re.S)
must(pat.search(s), 'redeem click price block')
s = pat.sub('''          // Net amount after the 10% fee (new Operations) at the price the contract will actually use
          const q = await getRedeemQuote();
          if (!(q.price > 0)) throw new Error("BCF price unavailable");
          const expectedUsdt = (bcfAmount * q.price * q.netFactor).toFixed(2);
          const minUsdtOut = ethers.parseUnits((Number(expectedUsdt) * 0.95).toFixed(2), 18);
''', s, count=1)

# ---------- #2 Buy plan text (8.1 split) ----------
rep('<span style="color:var(--muted);">Entry Fee (5%):</span>', '<span style="color:var(--muted);">50% → BCF <span style="font-size:0.7rem;">(30% fund · 20% marketing)</span>:</span>')
rep('style="color:var(--red);" id="planEntryFee"', 'style="color:var(--gold);" id="planEntryFee"')
rep('<span style="color:var(--muted);">Net Deposit:</span>', '<span style="color:var(--muted);">Principal (monthly return base):</span>')
a = s.index('      function recalcInvest() {')
b = s.index('\n      }\n', a) + 9
NEW_RECALC = '''      let _buyPx = 0;
      (async () => {
        try {
          const ops = getContract("Operations");
          let p; try { p = await ops.getBuyPrice(); } catch (e2) { p = await ops.getBCFPrice(); }
          _buyPx = Number(ethers.formatUnits(p, 18));
          recalcInvest();
        } catch (e) {}
      })();
      function recalcInvest() {
        if (!planAmount) return;
        const amt = Number(planAmount.value || 0);
        const plan = CONFIG.plans[_selectedPlan];
        const half = amt * 0.5;
        const monthly = (amt * plan.monthly) / 100;
        const ef = document.getElementById("planEntryFee");
        const pn = document.getElementById("planNet");
        const pm = document.getElementById("planMonthly");
        if (ef) ef.textContent = _buyPx > 0 ? `≈ ${(half / _buyPx).toFixed(2)} BCF (${half.toFixed(2)} USDT)` : `${half.toFixed(2)} USDT`;
        if (pn) pn.textContent = `${amt.toFixed(2)} USDT`;
        if (pm) pm.textContent = `+${monthly.toFixed(2)} USDT / month`;
      }
'''
s = s[:a] + NEW_RECALC + s[b:]
rep('''          const net = Number(amt) * 0.95;
          const halfUsdt = net * 0.5;''', '''          const halfUsdt = Number(amt) * 0.5;''')
rep('            const p = await ops.getBCFPrice();\n            const price', '            let p; try { p = await ops.getBuyPrice(); } catch (e2) { p = await ops.getBCFPrice(); }\n            const price')

# ---------- #3 Insurance claim: return BCF ----------
rep('''          for (const item of pending) {
            const ok = confirm(`Claim protection for Plan #${item.id}?\\n\\nProtection amount: ${ethers.formatUnits(item.protection, 18)} USDT\\n\\nNote: Insurance pool may be empty — owner must fund it first.`);''',
'''          for (const item of pending) {
            let bcfReq = 0n;
            try { bcfReq = await insC.getBcfRequired(item.id); } catch (e) {}
            const bcfNote = bcfReq > 0n ? `\\n\\nYou must return ${Number(ethers.formatUnits(bcfReq, 18)).toLocaleString(undefined, { maximumFractionDigits: 2 })} BCF (the BCF you received at purchase) to claim.` : "";
            const ok = confirm(`Claim protection for Plan #${item.id}?\\n\\nProtection amount: ${ethers.formatUnits(item.protection, 18)} USDT${bcfNote}\\n\\nNote: Insurance pool may be empty — owner must fund it first.`);''', label='ins confirm')
rep('''              const tx = await insC.claimInsurance(item.id);''', '''              if (bcfReq > 0n) {
                const bcfRead = getContract("BCFToken");
                const bcfBal = await bcfRead.balanceOf(state.account);
                if (bcfBal < bcfReq) {
                  alert(`You need ${ethers.formatUnits(bcfReq, 18)} BCF in your wallet to claim (you have ${ethers.formatUnits(bcfBal, 18)}).`);
                  break;
                }
                const allow = await bcfRead.allowance(state.account, CONFIG.addresses.Insurance);
                if (allow < bcfReq) {
                  claimInsProtect.textContent = "⏳ Approving BCF...";
                  const txA = await getContract("BCFToken", true).approve(CONFIG.addresses.Insurance, bcfReq);
                  await txA.wait();
                }
                claimInsProtect.textContent = "⏳ Claiming #" + item.id + "...";
              }
              const tx = await insC.claimInsurance(item.id);''', label='claimInsurance call')

# ---------- #4 Node credit ----------
s = s.replace('🎁 Claim Node Reward (BCF)', '🎁 Claim Node Reward (75% USDT + 25% Credit)')
rep('''          <div class="tier-progress">
            ${CONFIG.tiers.map((t, i, arr) => `
              <div class="tier-pip" style="width:auto;height:auto;background:transparent;border:0;padding:0;opacity:0.5;">
                ${tierIcon(t.type, 50)}
              </div>
              ${i < arr.length - 1 ? `<div class="tier-line"></div>` : ''}
            `).join('')}
          </div>
          <button class="btn-gold full" id="claimNodeReward"''', '''          <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;background:var(--bg-elev);border-radius:8px;padding:10px 12px;margin-top:14px;font-size:0.85rem;">
            <span style="color:var(--muted);">Credit balance <span style="font-size:0.7rem;">(25% of rewards · spend on Node only)</span></span>
            <span style="color:var(--gold);font-weight:700;white-space:nowrap;"><span id="nodeCredit">0</span> USDT</span>
          </div>
          <div class="tier-progress">
            ${CONFIG.tiers.map((t, i, arr) => `
              <div class="tier-pip" style="width:auto;height:auto;background:transparent;border:0;padding:0;opacity:0.5;">
                ${tierIcon(t.type, 50)}
              </div>
              ${i < arr.length - 1 ? `<div class="tier-line"></div>` : ''}
            `).join('')}
          </div>
          <button class="btn-gold full" id="claimNodeReward"''', label='node card')
rep('''        <h3 style="color:var(--muted);font-size:0.9rem;margin:24px 0 12px;">Available Node Tiers</h3>''', '''        <div class="stat-card" style="margin-bottom:20px;">
          <h3 style="font-size:0.95rem;margin-bottom:8px;color:var(--gold);">Buy Node with Credit</h3>
          <p style="color:var(--muted);font-size:0.8rem;margin-bottom:12px;line-height:1.5;">Credit comes from the 25% share of Node and referral rewards. It can only be spent on Node shares (100 USDT = 1 share). You can top up with extra USDT.</p>
          <div class="form-row"><label>Credit to use (USDT)</label><input type="number" id="nodeCreditAmt" value="100" min="0" step="100" /></div>
          <div class="form-row"><label>Extra USDT from wallet (optional)</label><input type="number" id="nodeCreditUsdt" value="0" min="0" step="100" /></div>
          <button class="btn-gold full" id="nodeCreditBuy" ${!state.deployed ? 'disabled' : ''}>💎 Buy Node with Credit</button>
        </div>

        <h3 style="color:var(--muted);font-size:0.9rem;margin:24px 0 12px;">Available Node Tiers</h3>''', label='available node tiers')
rep('            if (sharesEl) sharesEl.textContent = info[2].toString();', '''            if (sharesEl) sharesEl.textContent = info[2].toString();
            try {
              const cr = await getContract("Operations").getCredit(state.account);
              const crEl = document.getElementById("nodeCredit");
              if (crEl) crEl.textContent = Number(ethers.formatUnits(cr, 18)).toLocaleString(undefined, { maximumFractionDigits: 2 });
            } catch (e) {}''', label='node load shares')
rep('      // Node — Load user data', '''      // Node — Buy with Credit
      const nodeCreditBuy = document.getElementById("nodeCreditBuy");
      if (nodeCreditBuy) nodeCreditBuy.addEventListener("click", () => buyNodeWithCreditUI(nodeCreditBuy));

      // Node — Load user data''')
rep('    async function buyNodeShares(amountU, btn) {', '''    async function buyNodeWithCreditUI(btn) {
      if (!state.account) { await connectWallet(); return; }
      if (!state.chainOk) { await switchToBSC(); return; }
      const creditU = Number(document.getElementById("nodeCreditAmt").value || 0);
      const usdtU = Number(document.getElementById("nodeCreditUsdt").value || 0);
      if (creditU + usdtU < 100) { alert("Minimum 100 USDT-equivalent (1 share)"); return; }
      const oldText = btn.textContent;
      try {
        btn.disabled = true;
        btn.textContent = "⏳ Checking credit...";
        const creditWei = ethers.parseUnits(String(creditU), 18);
        const usdtWei = ethers.parseUnits(String(usdtU), 18);
        const bal = await getContract("Operations").getCredit(state.account);
        if (creditWei > bal) {
          alert(`Not enough credit. You have ${Number(ethers.formatUnits(bal, 18)).toFixed(2)} USDT of credit.`);
          btn.disabled = false; btn.textContent = oldText; return;
        }
        if (!confirm(`Buy ${Math.floor((creditU + usdtU) / 100)} node share(s)?\\n\\nCredit used: ${creditU} USDT\\nWallet USDT: ${usdtU} USDT`)) {
          btn.disabled = false; btn.textContent = oldText; return;
        }
        if (usdtWei > 0n) {
          const usdt = getContract("MockUSDT");
          const allow = await usdt.allowance(state.account, CONFIG.addresses.Node);
          if (allow < usdtWei) {
            btn.textContent = "⏳ Approving USDT...";
            const txA = await getContract("MockUSDT", true).approve(CONFIG.addresses.Node, usdtWei);
            await txA.wait();
          }
        }
        btn.textContent = "⏳ Buying...";
        const tx = await getContract("Node", true).buyNodeWithCredit(usdtWei, creditWei);
        await tx.wait();
        alert(`✅ Node shares purchased with credit!\\n\\nTx: ${tx.hash}\\nView: https://testnet.bscscan.com/tx/${tx.hash}`);
        btn.disabled = false; btn.textContent = oldText;
        render();
      } catch (e) {
        alert("Buy with Credit failed: " + (e.reason || e.message));
        btn.disabled = false; btn.textContent = oldText;
      }
    }

    async function buyNodeShares(amountU, btn) {''')

# ---------- #5 Referral: deep link + auto fill + lock ----------
rep('<label>Referrer (optional, 0x...)</label>', '<label>Referrer (auto-linked on your first purchase, then locked)</label>')
rep('      const planReferrer = document.getElementById("planReferrer");', '''      const planReferrer = document.getElementById("planReferrer");
      if (planReferrer) {
        try { const saved = localStorage.getItem("bcf_referrer"); if (saved && !planReferrer.value) planReferrer.value = saved; } catch (e) {}
        if (state.account && state.deployed) {
          (async () => {
            try {
              const u = await getContract("Referral").users(state.account);
              const r = u[0];
              if (r && r !== ethers.ZeroAddress) {
                planReferrer.value = r;
                planReferrer.disabled = true;
                const lbl = planReferrer.previousElementSibling;
                if (lbl) lbl.textContent = "Referrer (locked on-chain)";
              }
            } catch (e) {}
          })();
        }
      }''', label='planReferrer')
rep('    window.addEventListener("hashchange", render);', '''    // Referral deep link: /ref/0x... or ?ref=0x...  -> remember it and jump to the buy page
    (function captureReferral() {
      try {
        const m = location.pathname.match(/\\/ref\\/(0x[a-fA-F0-9]{40})/) || location.search.match(/[?&]ref=(0x[a-fA-F0-9]{40})/);
        if (m) {
          localStorage.setItem("bcf_referrer", m[1]);
          if (location.pathname.indexOf("/ref/") === 0) history.replaceState(null, "", "/" + (location.hash || ""));
          if (!location.hash || location.hash === "#/dashboard") location.hash = "#/invest";
        }
      } catch (e) {}
    })();

    window.addEventListener("hashchange", render);''', label='hashchange')

shutil.copyfile(PATH, PATH + '.v62.bak')
open(PATH, 'w', encoding='utf-8').write(s)
print('OK  patched', PATH, '(backup: ' + PATH + '.v62.bak)')