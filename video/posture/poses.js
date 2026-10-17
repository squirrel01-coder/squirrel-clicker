const FL = 880, D2R = Math.PI / 180;
const L = { torso: 150, neck: 22, head: 36, ua: 84, fa: 80, th: 112, sh: 106 };
const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const p01 = (t, a, b) => clamp((t - a) / (b - a));
const sm = v => v * v * (3 - 2 * v);
const eo = v => 1 - Math.pow(1 - v, 3);
const eb = v => { const s = 1.7; return v <= 0 ? 0 : 1 + (s + 1) * Math.pow(v - 1, 3) + s * Math.pow(v - 1, 2); };
const lerp = (a, b, k) => a + (b - a) * k;
const osc = (t, per) => .5 - .5 * Math.cos(2 * Math.PI * t / per);
function holdC(t, up, hold, down, rest) { const P = up + hold + down + rest, u = ((t % P) + P) % P; if (u < up) return sm(u / up); if (u < up + hold) return 1; if (u < up + hold + down) return 1 - sm((u - up - hold) / down); return 0; }
const dd = a => ({ x: Math.sin(a * D2R), y: Math.cos(a * D2R) });
const add = (A, v, k = 1) => ({ x: A.x + v.x * k, y: A.y + v.y * k });
const ang = (A, B) => Math.atan2(B.x - A.x, B.y - A.y) / D2R;
function ik(A, B, l1, l2, bend) { const dx = B.x - A.x, dy = B.y - A.y, d = clamp(Math.hypot(dx, dy), 1, l1 + l2 - .01), base = Math.atan2(dx, dy) / D2R;
  const off = Math.acos(clamp((l1 * l1 + d * d - l2 * l2) / (2 * l1 * d), -1, 1)) / D2R, a1 = base + bend * off, J = add(A, dd(a1), l1); return [a1, ang(J, B)]; }
function anchors(p) { const t = dd(p.torso), n = { x: -t.y, y: t.x }, S0 = add(p.P, t, L.torso - 12), N = add(p.P, t, L.torso);
  if (p.view === 'front') return { t, n, S0, N, SA: add(S0, n, 50), SB: add(S0, n, -50), HA: add(p.P, n, 24), HB: add(p.P, n, -24) };
  return { t, n, S0, N, SA: S0, SB: add(S0, { x: -3, y: -2 }), HA: p.P, HB: add(p.P, { x: -3, y: -2 }) }; }
function stand(xc, view = 'side') { const p = { view, P: { x: xc, y: FL - 12 - L.th - L.sh + 3 }, torso: 180, neck: 180, armA: [6, 10], armB: [4, 8] };
  const A = anchors(p); const fx = view === 'front' ? 30 : 6; p.legA = ik(A.HA, { x: A.HA.x + (view === 'front' ? 12 : 4), y: FL - 12 }, L.th, L.sh, 1); p.legB = ik(A.HB, { x: A.HB.x - (view === 'front' ? 12 : 4), y: FL - 12 }, L.th, L.sh, 1);
  if (view === 'front') { p.armA = [12, 8]; p.armB = [-12, -8]; } return p; }
function quad(Px, neutralCurve = [0, 0], neck = 100) { const P = { x: Px, y: FL - 14 - L.th }, Hd = { x: Px + 131, y: FL - 12 };
  const p = { view: 'side', P, torso: 110, neck, curve: neutralCurve }; const A = anchors(p);
  p.armA = ik(A.SA, Hd, L.ua, L.fa, -1); p.armB = ik(A.SB, { x: Hd.x - 4, y: Hd.y }, L.ua, L.fa, -1);
  p.legA = [ang(P, { x: Px, y: FL - 14 }), -90]; p.legB = [ang(P, { x: Px - 3, y: FL - 14 }), -90]; return p; }
const EX = {
  chin: { view: 'side', k: 1.25, props(t) { wall(260, 512); }, pose(t) { const q = holdC(t, .8, 2.2, .8, .7), p = stand(560); p.neck = 156 + 28 * q; p.armA = [2, 4]; p.armB = [1, 2]; return p; },
    fx(t, r) { const q = holdC(t, .8, 2.2, .8, .7); arrow(r.Hc.x + 70, r.Hc.y, r.Hc.x + 20 - 40 * q, r.Hc.y, C.blue, q > .05 && q < .99 ? 1 : .35); tag(q > .95 ? 'держим 5 сек' : 'затылок назад', r.Hc.x + 30, r.Hc.y - 110, q > .95 ? C.ok : C.blue); } },
  angel: { view: 'front', k: 1.2, props(t) { x.fillStyle = '#C9D7E6'; rr(330, 150, 460, FL - 150, 10); x.fill(); },
    pose(t) { const q = osc(t, 3.4), p = stand(560, 'front'); p.armA = [92 + 62 * q, 180 - 18 * q]; p.armB = [-(92 + 62 * q), -(180 - 18 * q)]; return p; },
    fx(t, r) { tag(osc(t, 3.4) > .5 ? 'вверх ↑' : 'локти к стене', 560, 190, C.blue); } },
  door: { view: 'side', k: 1.25, props(t) { x.fillStyle = '#A16207'; rr(472, 230, 30, FL - 230, 6); x.fill(); x.fillStyle = '#CA8A04'; rr(472, 230, 30, 14, 4); x.fill(); },
    pose(t) { const q = holdC(t, 1.5, 3, 1.5, .5), p = stand(580); p.torso = 180 - 9 * q; p.neck = 180 - 6 * q; const A = anchors(p);
      p.legA = ik(A.HA, { x: 650, y: FL - 12 }, L.th, L.sh, 1); p.legB = ik(A.HB, { x: 520, y: FL - 12 }, L.th, L.sh, 1);
      const el = { x: 500, y: A.S0.y + 4 }; const ua = ang(A.S0, el); p.armA = [ua, 178]; p.armB = [ua - 2, 176]; return p; },
    fx(t, r) { const q = holdC(t, 1.5, 3, 1.5, .5); x.save(); x.globalAlpha = .25 + .5 * q; x.fillStyle = '#F43F5E'; x.beginPath(); x.ellipse(r.A.S0.x + 26, r.A.S0.y + 34, 26, 34, 0, 0, 7); x.fill(); x.restore(); tag('шаг вперёд', 650, 230, C.blue); } },
  towelroll: { view: 'side', mat: 1, props(t) { towelRoll(492, FL - 26); },
    pose(t) { const q = holdC(t, 1.2, 1.4, 1.2, .5), P = { x: 640, y: FL - 34 }, p = { view: 'side', P, torso: -94 + 14 * q, neck: -86 + 4 * q, curve: [0, -16 * q] }; const A = anchors(p);
      p.legA = ik(P, { x: 800, y: FL - 12 }, L.th, L.sh, 1); p.legB = ik(P, { x: 795, y: FL - 14 }, L.th, L.sh, 1);
      const Hc = add(A.N, dd(p.neck), L.neck + L.head - 6), tg = { x: Hc.x + 10, y: Hc.y + 24 }; p.armA = ik(A.SA, tg, L.ua, L.fa, -1); p.armB = ik(A.SB, { x: tg.x - 4, y: tg.y - 4 }, L.ua, L.fa, -1); return p; },
    fx(t, r) { tag('валик под лопатками', 492, FL - 150, C.gold); } },
  sidebend: { view: 'front', k: 1.25, pose(t) { const q = holdC(t, 1.3, 2.6, 1.3, .4), p = stand(560, 'front'); p.torso = 180 - 17 * q; const A = anchors(p);
      p.armB = [180 - 26 * q, 178 - 40 * q]; p.armA = ik(A.SA, add(A.HA, { x: 18, y: -16 }), L.ua, L.fa, 1); return p; },
    fx(t, r) { const q = holdC(t, 1.3, 2.6, 1.3, .4); arrow(r.hands.B.x - 10, r.hands.B.y - 30, r.hands.B.x + 70, r.hands.B.y - 10, C.blue, q); tag('правый бок тянется', 560, 140, C.blue); } },
  catcow: { view: 'side', mat: 1, pose(t) { const s = Math.cos(2 * Math.PI * t / 5), cat = Math.max(0, s), cow = Math.max(0, -s);
      return quad(470, [0, -42 * cat + 24 * cow], 100 - 48 * cat + 32 * cow); },
    fx(t) { const s = Math.cos(2 * Math.PI * t / 5); tag(s > 0 ? 'выдох — спина вверх' : 'вдох — прогиб', 560, 520, s > 0 ? C.blue : C.teal); } },
  yw: { view: 'side', mat: 1, pose(t) { const ph = t % 8, Y = ph < 4, l = osc(ph, 2), P = { x: 420, y: FL - 26 }, p = { view: 'side', P, torso: 90, neck: 86, legA: [-90, -86], legB: [-89, -85] };
      if (Y) { p.armA = [90 + 13 * l, 90 + 15 * l]; p.armB = [89 + 13 * l, 89 + 15 * l]; } else { p.armA = [-72 - 26 * l, 62 + 30 * l]; p.armB = [-71 - 26 * l, 61 + 30 * l]; } return p; },
    fx(t) { const Y = (t % 8) < 4; T(Y ? 'руки вперёд' : 'локти к рёбрам', 560, 560, 46, { fill: C.blue }); } },
  pullapart: { view: 'front', k: 1.25, pose(t) { const q = osc(t, 2.6), p = stand(560, 'front'); const s = .45 + .55 * q; p.armA = [62 + 30 * q, 66 + 26 * q, s, 1]; p.armB = [-(62 + 30 * q), -(66 + 26 * q), s, 1]; return p; },
    fx(t, r) { const a = r.hands.A, b = r.hands.B; x.strokeStyle = '#FB923C'; x.lineWidth = 20; x.lineCap = 'round'; x.beginPath(); x.moveTo(b.x, b.y); x.quadraticCurveTo((a.x + b.x) / 2, (a.y + b.y) / 2 + 10, a.x, a.y); x.stroke(); tag('сжимаем лопатки', 560, 170, C.blue); } },
  scap: { view: 'side', mat: 1, pose(t) { const dr = 16 * osc(t, 2.2), Hd = { x: 720, y: FL - 12 }, S0 = { x: 720, y: FL - 12 - 160 + dr }, Ft = { x: 250, y: FL - 12 };
      const u = { x: Ft.x - S0.x, y: Ft.y - S0.y }, ul = Math.hypot(u.x, u.y), P = { x: S0.x + u.x / ul * (L.torso - 12), y: S0.y + u.y / ul * (L.torso - 12) };
      const p = { view: 'side', P, torso: ang(P, S0), neck: ang(P, S0) - 6 }; const A = anchors(p);
      p.armA = ik(A.SA, Hd, L.ua, L.fa, -1); p.armB = ik(A.SB, { x: Hd.x - 4, y: Hd.y }, L.ua, L.fa, -1); p.legA = ik(P, Ft, L.th, L.sh, 1); p.legB = ik(P, { x: Ft.x - 4, y: Ft.y }, L.th, L.sh, 1); return p; },
    fx(t, r) { tag('руки прямые', 720, 560, C.blue); } },
  sideplank: { view: 'front', mat: 1, pose(t) { const lift = 10 * osc(t, 3), S0 = { x: 745, y: FL - 152 }, Ft = { x: 250, y: FL - 16 };
      const u = { x: Ft.x - S0.x, y: Ft.y - S0.y }, ul = Math.hypot(u.x, u.y), P = { x: S0.x + u.x / ul * (L.torso - 12), y: S0.y + u.y / ul * (L.torso - 12) - lift };
      const p = { view: 'front', P, torso: ang(P, S0) }; p.neck = p.torso; const A = anchors(p);
      const E = { x: A.SA.x, y: FL - 14 }; p.armA = [ang(A.SA, E), 90, .45]; p.armB = ik(A.SB, add(P, A.n, -30), L.ua, L.fa, 1);
      p.legA = ik(A.HA, Ft, L.th, L.sh, -1); p.legB = ik(A.HB, { x: Ft.x + 6, y: Ft.y - 26 }, L.th, L.sh, -1); return p; },
    fx(t, r) { tag('тело — одна линия', 520, 560, C.blue); tag('левый бок: 3 × 40 сек', 520, 640, C.ok); } },
  birddog: { view: 'side', mat: 1, pose(t) { const k = Math.floor(t / 3.2) % 2, e = holdC(t % 3.2, .9, 1.2, .9, .2), p = quad(470, [0, 0], 100);
      const AR = [92, 92], LG = [-86, -88];
      if (k === 0) { p.armA = [lerp(p.armA[0], AR[0], e), lerp(p.armA[1], AR[1], e)]; p.legB = [lerp(p.legB[0], LG[0], e), lerp(p.legB[1], LG[1], e)]; }
      else { p.armB = [lerp(p.armB[0], AR[0], e), lerp(p.armB[1], AR[1], e)]; p.legA = [lerp(p.legA[0], LG[0], e), lerp(p.legA[1], LG[1], e)]; } return p; },
    fx(t) { tag('спина как стол', 560, 520, C.blue); } },
  deadbug: { view: 'side', mat: 1, pose(t) { const k = Math.floor(t / 3.2) % 2, e = holdC(t % 3.2, .9, 1, .9, .4), P = { x: 640, y: FL - 32 };
      const p = { view: 'side', P, torso: -90, neck: -85, armA: [180, 180], armB: [181, 181], legA: [180, 90], legB: [179, 89] };
      const armX = [lerp(180, 262, e), lerp(180, 266, e)], legX = [lerp(180, 97, e), lerp(90, 96, e)];
      if (k === 0) { p.armB = armX; p.legA = legX; } else { p.armA = armX; p.legB = legX; } return p; },
    fx(t) { tag('поясница прижата', 600, 560, C.blue); } },
  bridge: { view: 'side', mat: 1, pose(t) { const q = holdC(t, 1, .9, 1, .4), h = 92 * q, S0 = { x: 470, y: FL - 34 }, dx = Math.sqrt((L.torso - 12) ** 2 - h * h), P = { x: S0.x + dx, y: FL - 34 - h };
      const p = { view: 'side', P, torso: ang(P, S0), neck: -85, armA: [84, 86], armB: [83, 85] }; p.legA = ik(P, { x: 775, y: FL - 12 }, L.th, L.sh, 1); p.legB = ik(P, { x: 770, y: FL - 14 }, L.th, L.sh, 1); return p; },
    fx(t) { const q = holdC(t, 1, .9, 1, .4); tag(q > .95 ? 'сжать ягодицы!' : 'толкаемся пятками', 620, 520, q > .95 ? C.ok : C.blue); } },
  split: { view: 'side', k: 1.25, pose(t) { const q = osc(t, 2.8), P = { x: 520, y: FL - 12 - 205 + 92 * q }, p = { view: 'side', P, torso: 180, neck: 180 }; const A = anchors(p);
      p.legA = ik(P, { x: 615, y: FL - 12 }, L.th, L.sh, 1); p.legB = ik(P, { x: 370, y: FL - 22 }, L.th, L.sh, 1);
      p.armA = ik(A.SA, { x: P.x + 22, y: P.y - 22 }, L.ua, L.fa, -1); p.armB = ik(A.SB, { x: P.x + 18, y: P.y - 24 }, L.ua, L.fa, -1); return p; },
    fx(t) { tag('корпус прямо', 520, 360, C.blue); } },
  hang: { view: 'front', k: 1.0, props(t) { x.fillStyle = '#475569'; rr(330, 168, 460, 16, 8); x.fill(); x.fillRect(330, 168, 12, 110); x.fillRect(778, 168, 12, 110); },
    pose(t) { const s = 3 * Math.sin(t * 1.3), S0 = { x: 560 + s * 2, y: 345 }, p = { view: 'front', torso: 180 + s, neck: 180 + s }; const tt = dd(p.torso); p.P = add(S0, tt, -(L.torso - 12)); const A = anchors(p);
      p.armA = ik(A.SA, { x: 645, y: 178 }, L.ua, L.fa, 1); p.armB = ik(A.SB, { x: 475, y: 178 }, L.ua, L.fa, -1);
      p.legA = [s * .8 + 2, s + 3]; p.legB = [s * .8 - 2, s - 3]; return p; },
    fx(t) { tag('плечи от ушей', 560, 120, C.blue); } },
};
function sitter(k, t) { const P = { x: 470, y: FL - 12 - L.sh - 2 }, p = { view: 'side', P, torso: lerp(158, 181, k), neck: lerp(122, 180, k), curve: [lerp(-30, 0, k), lerp(-8, 0, k)] };
  const A = anchors(p); p.legA = [90, 0]; p.legB = [89, -1]; const kb = { x: lerp(735, 700, k), y: lerp(FL - 288, FL - 290, k) + Math.sin(t * 9) * 3 * (1 - k) };
  p.armA = ik(A.SA, kb, L.ua, L.fa, -1); p.armB = ik(A.SB, { x: kb.x + 14, y: kb.y }, L.ua, L.fa, -1); return p; }
const C = {}; function wall(){} function towelRoll(){} function rr(){} function tag(){} function arrow(){} function T(){}
