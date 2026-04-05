<template>
  <div class="landing">

    <!-- ── NAV ─────────────────────────────────────────────── -->
    <header class="lp-nav">
      <div class="lp-nav__inner">
        <div class="lp-nav__brand">
          <CarIcon class="brand-icon" />
          <span class="brand-name">DriveEase</span>
        </div>
        <nav class="lp-nav__links">
          <a href="#vehicles">Vehicles</a>
          <a href="#how-it-works">How It Works</a>
          <a href="#pricing">Pricing</a>
        </nav>
        <RouterLink to="/login" class="btn btn--outline">Sign In</RouterLink>
      </div>
    </header>

    <!-- ── HERO ───────────────────────────────────────────── -->
    <section class="hero">
      <div class="hero__bg">
        <div class="hero__grid" aria-hidden="true"></div>
        <div class="hero__orb hero__orb--1" aria-hidden="true"></div>
        <div class="hero__orb hero__orb--2" aria-hidden="true"></div>
      </div>
      <div class="hero__content">
        <div class="hero__badge">
          <ZapIcon class="badge-icon" />
          <span>Instant Booking · Pay by the Hour</span>
        </div>
        <h1 class="hero__headline">
          Drive anywhere,<br />
          <span class="hero__headline--accent">on your terms</span>
        </h1>
        <p class="hero__sub">
          Premium cars, hourly pricing, zero hassle. Book in seconds,
          pay securely via Stripe, and hit the road.
        </p>
        <div class="hero__cta-row">
          <RouterLink to="/book-car" class="btn btn--primary btn--lg">
            Book a Car Now
            <ArrowRightIcon class="btn-icon" />
          </RouterLink>
          <a href="#how-it-works" class="btn btn--ghost btn--lg">See how it works</a>
        </div>
        <div class="hero__trust">
          <div class="trust-item">
            <ShieldCheckIcon class="trust-icon" />
            <span>Stripe-secured payments</span>
          </div>
          <div class="trust-item">
            <MapPinIcon class="trust-icon" />
            <span>Google Maps integration</span>
          </div>
          <div class="trust-item">
            <RefreshCwIcon class="trust-icon" />
            <span>Flexible cancellation</span>
          </div>
        </div>
      </div>

      <!-- floating car card mockup -->
      <div class="hero__card-demo" aria-hidden="true">
        <div class="demo-card">
          <div class="demo-card__header">
            <div class="demo-card__dot demo-card__dot--red"></div>
            <div class="demo-card__dot demo-card__dot--amber"></div>
            <div class="demo-card__dot demo-card__dot--green"></div>
            <span class="demo-card__title">Booking Confirmed</span>
          </div>
          <div class="demo-card__body">
            <div class="demo-car-visual">
              <CarIcon class="demo-car-icon" />
            </div>
            <div class="demo-info">
              <div class="demo-info__row">
                <span class="demo-info__label">Vehicle</span>
                <span class="demo-info__value">Premium Sedan</span>
              </div>
              <div class="demo-info__row">
                <span class="demo-info__label">Duration</span>
                <span class="demo-info__value">4 hours</span>
              </div>
              <div class="demo-info__row">
                <span class="demo-info__label">Total</span>
                <span class="demo-info__value demo-info__value--accent">$50.00</span>
              </div>
            </div>
          </div>
          <div class="demo-card__status">
            <CheckCircleIcon class="status-icon" />
            <span>Payment processed · Ready to drive</span>
          </div>
        </div>
      </div>
    </section>

    <!-- ── VEHICLES ───────────────────────────────────────── -->
    <section id="vehicles" class="section section--light">
      <div class="container">
        <div class="section__header">
          <h2 class="section__title">Choose your ride</h2>
          <p class="section__sub">Three classes of premium vehicles, all available by the hour.</p>
        </div>
        <div class="vehicles-grid">
          <div
            v-for="v in vehicles"
            :key="v.type"
            class="vehicle-card"
            :class="`vehicle-card--${v.accent}`"
          >
            <div class="vehicle-card__icon-wrap">
              <component :is="v.icon" class="vehicle-card__icon" />
            </div>
            <h3 class="vehicle-card__name">{{ v.name }}</h3>
            <p class="vehicle-card__desc">{{ v.desc }}</p>
            <ul class="vehicle-card__features">
              <li v-for="f in v.features" :key="f">
                <CheckIcon class="feature-check" />
                <span>{{ f }}</span>
              </li>
            </ul>
            <div class="vehicle-card__footer">
              <div class="vehicle-card__price">
                <span class="price-amount">{{ v.price }}</span>
                <span class="price-unit">/hr</span>
              </div>
              <RouterLink to="/book-car" class="btn btn--sm btn--primary">Book now</RouterLink>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ── HOW IT WORKS ───────────────────────────────────── -->
    <section id="how-it-works" class="section section--dark">
      <div class="container">
        <div class="section__header section__header--light">
          <h2 class="section__title">Three steps to the road</h2>
          <p class="section__sub section__sub--muted">From signup to driving in under two minutes.</p>
        </div>
        <div class="steps-grid">
          <div v-for="(step, i) in steps" :key="step.title" class="step-card">
            <div class="step-card__number">{{ String(i + 1).padStart(2, '0') }}</div>
            <div class="step-card__icon-wrap">
              <component :is="step.icon" class="step-card__icon" />
            </div>
            <h3 class="step-card__title">{{ step.title }}</h3>
            <p class="step-card__desc">{{ step.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- ── FEATURES ───────────────────────────────────────── -->
    <section class="section section--light">
      <div class="container">
        <div class="features-split">
          <div class="features-split__copy">
            <h2 class="section__title">Built for the modern driver</h2>
            <p class="features-split__body">
              A microservices platform handling everything behind the scenes —
              so your only job is to drive.
            </p>
            <ul class="features-list">
              <li v-for="f in features" :key="f.title" class="features-list__item">
                <div class="features-list__icon-wrap">
                  <component :is="f.icon" class="features-list__icon" />
                </div>
                <div>
                  <strong class="features-list__title">{{ f.title }}</strong>
                  <p class="features-list__desc">{{ f.desc }}</p>
                </div>
              </li>
            </ul>
          </div>
          <div class="features-split__visual" aria-hidden="true">
            <div class="dash-mockup">
              <div class="dash-mockup__bar">
                <span class="dash-mockup__label">Service Dashboard</span>
                <span class="dash-mockup__live"><span class="live-dot"></span>Live</span>
              </div>
              <div class="dash-mockup__row" v-for="n in 4" :key="n">
                <div class="dash-mockup__pill" :style="{ width: `${55 + n * 10}%` }"></div>
                <div class="dash-mockup__badge" :class="n % 2 === 0 ? 'badge--green' : 'badge--amber'">
                  {{ n % 2 === 0 ? 'Resolved' : 'Pending' }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ── PRICING ─────────────────────────────────────────── -->
    <section id="pricing" class="section section--light">
      <div class="container">
        <div class="section__header">
          <h2 class="section__title">Simple, transparent pricing</h2>
          <p class="section__sub">Pay only for the hours you drive. No subscriptions, no surprises.</p>
        </div>
        <div class="pricing-grid">
          <div
            v-for="p in pricing"
            :key="p.type"
            class="pricing-card"
            :class="{ 'pricing-card--featured': p.featured }"
          >
            <div v-if="p.featured" class="pricing-card__badge">Most Popular</div>
            <div class="pricing-card__icon-wrap">
              <component :is="p.icon" class="pricing-card__icon" />
            </div>
            <h3 class="pricing-card__name">{{ p.name }}</h3>
            <div class="pricing-card__rate">
              <span class="rate-dollar">$</span>
              <span class="rate-amount">{{ p.rate }}</span>
              <span class="rate-unit">/hr</span>
            </div>
            <p class="pricing-card__desc">{{ p.desc }}</p>
            <ul class="pricing-card__includes">
              <li v-for="item in p.includes" :key="item">
                <CheckIcon class="check-icon" />{{ item }}
              </li>
            </ul>
            <RouterLink
              to="/book-car"
              class="btn btn--block"
              :class="p.featured ? 'btn--primary' : 'btn--outline'"
            >
              Get started
            </RouterLink>
          </div>
        </div>
        <p class="pricing-note">
          <InfoIcon class="note-icon" />
          Cancellations made &gt;24 hours before: full refund. 1–24 hours: 50% refund. Under 1 hour: no refund.
        </p>
      </div>
    </section>

    <!-- ── FINAL CTA ───────────────────────────────────────── -->
    <section class="cta-banner">
      <div class="cta-banner__orb" aria-hidden="true"></div>
      <div class="container">
        <h2 class="cta-banner__headline">Ready to drive?</h2>
        <p class="cta-banner__sub">Create a free account and book your first car in under 2 minutes.</p>
        <RouterLink to="/book-car" class="btn btn--primary btn--lg btn--wide">
          Book a Car Now
          <ArrowRightIcon class="btn-icon" />
        </RouterLink>
      </div>
    </section>

    <!-- ── FOOTER ──────────────────────────────────────────── -->
    <footer class="footer">
      <div class="container footer__inner">
        <div class="footer__brand">
          <CarIcon class="brand-icon" />
          <span class="brand-name">DriveEase</span>
        </div>
        <p class="footer__copy">© 2026 DriveEase. All rights reserved.</p>
      </div>
    </footer>

  </div>
</template>

<script setup>
import {
  Car as CarIcon,
  Zap as ZapIcon,
  ArrowRight as ArrowRightIcon,
  ShieldCheck as ShieldCheckIcon,
  MapPin as MapPinIcon,
  RefreshCw as RefreshCwIcon,
  Check as CheckIcon,
  CheckCircle as CheckCircleIcon,
  CreditCard as CreditCardIcon,
  Bell as BellIcon,
  Map as MapIcon,
  Brain as BrainIcon,
  Info as InfoIcon,
  Users as UsersIcon,
  Truck as TruckIcon,
} from 'lucide-vue-next'

const vehicles = [
  {
    type: 'sedan',
    accent: 'blue',
    icon: CarIcon,
    name: 'Sedan',
    price: '$12.50',
    desc: 'Comfortable and fuel-efficient — ideal for city commutes and daily errands.',
    features: ['Up to 5 passengers', 'Automatic transmission', 'AC & Bluetooth'],
  },
  {
    type: 'suv',
    accent: 'red',
    icon: UsersIcon,
    name: 'SUV',
    price: '$18.00',
    desc: 'Spacious and capable — perfect for families, road trips, or rough terrain.',
    features: ['Up to 7 passengers', 'All-wheel drive', 'Extra cargo space'],
  },
  {
    type: 'van',
    accent: 'amber',
    icon: TruckIcon,
    name: 'Van',
    price: '$15.00',
    desc: 'Maximum cargo and passenger capacity for group travel or large hauls.',
    features: ['Up to 8 passengers', 'Large cargo area', 'Sliding side doors'],
  },
]

const steps = [
  {
    icon: ShieldCheckIcon,
    title: 'Create your account',
    desc: 'Sign up with email and verify your driver details in seconds using Firebase Auth.',
  },
  {
    icon: CarIcon,
    title: 'Pick a vehicle',
    desc: 'Browse available sedans, SUVs, and vans on an interactive Google Maps view.',
  },
  {
    icon: CreditCardIcon,
    title: 'Pay & drive',
    desc: 'Checkout securely via Stripe. Your booking is confirmed instantly — no waiting.',
  },
]

const features = [
  {
    icon: BrainIcon,
    title: 'AI-powered incident reports',
    desc: 'Report issues with automatic GPS location and OpenAI severity classification.',
  },
  {
    icon: BellIcon,
    title: 'Real-time service updates',
    desc: 'Live WebSocket dashboard keeps service teams notified the moment an incident is logged.',
  },
  {
    icon: RefreshCwIcon,
    title: 'Smart cancellation refunds',
    desc: 'Policy-based refunds processed automatically through Stripe — no manual disputes.',
  },
  {
    icon: MapIcon,
    title: 'Location-aware booking',
    desc: 'Find the nearest available vehicle with an embedded Google Maps vehicle picker.',
  },
]

const pricing = [
  {
    type: 'sedan',
    icon: CarIcon,
    name: 'Sedan',
    rate: '12.50',
    featured: false,
    desc: 'Best for solo commuters and short city trips.',
    includes: ['Hourly billing', 'Stripe checkout', 'Flexible cancellation', 'AC & Bluetooth'],
  },
  {
    type: 'van',
    icon: TruckIcon,
    name: 'Van',
    rate: '15.00',
    featured: false,
    desc: 'Great for group travel or moving large items.',
    includes: ['Hourly billing', 'Stripe checkout', 'Flexible cancellation', 'Max cargo space'],
  },
  {
    type: 'suv',
    icon: UsersIcon,
    name: 'SUV',
    rate: '18.00',
    featured: true,
    desc: 'Ideal for families, road trips, and any terrain.',
    includes: ['Hourly billing', 'Stripe checkout', 'Flexible cancellation', 'AWD + 7 seats'],
  },
]
</script>

<style scoped>
/* ── TOKENS ─────────────────────────────────────────────────── */
:root {
  --color-primary:    #000000;
  --color-accent:     #DC2626;
  --color-bg:         #F8FAFC;
  --color-surface:    #FFFFFF;
  --color-border:     #E2E8F0;
  --color-muted:      #000000;
  --color-dark:       #000000;
  --font-sans:        'DM Sans', system-ui, sans-serif;
  --radius:           16px;
  --radius-sm:        10px;
  --shadow-card:      0 1px 3px rgba(0,0,0,0.07), 0 4px 16px rgba(0,0,0,0.06);
  --shadow-hover:     0 4px 24px rgba(0,0,0,0.12), 0 1px 4px rgba(0,0,0,0.08);
  --transition:       0.2s ease;
}

/* ── RESET / BASE ───────────────────────────────────────────── */
.landing {
  font-family: var(--font-sans);
  color: var(--color-dark);
  background: var(--color-bg);
  line-height: 1.6;
  overflow-x: hidden;
}

/* ── NAV ─────────────────────────────────────────────────────── */
.lp-nav {
  position: fixed;
  top: 0; left: 0; right: 0;
  z-index: 100;
  background: rgba(255,255,255,0.9);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--color-border);
}

.lp-nav__inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
  height: 64px;
  display: flex;
  align-items: center;
  gap: 32px;
}

.lp-nav__brand {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.brand-icon  { width: 22px; height: 22px; color: var(--color-accent); }
.brand-name  { font-size: 18px; font-weight: 700; color: var(--color-dark); letter-spacing: -0.3px; }

.lp-nav__links {
  display: flex;
  gap: 24px;
  margin-left: auto;
}

.lp-nav__links a {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-muted);
  text-decoration: none;
  transition: color var(--transition);
}
.lp-nav__links a:hover { color: var(--color-dark); }

/* ── BUTTONS ──────────────────────────────────────────────────── */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-sans);
  font-size: 14px;
  font-weight: 600;
  padding: 10px 20px;
  border-radius: 10px;
  border: none;
  cursor: pointer;
  text-decoration: none;
  transition: all var(--transition);
  white-space: nowrap;
}
.btn--primary  { background: #DC2626; color: #fff; box-shadow: 0 2px 8px rgba(220,38,38,0.25); }
.btn--primary:hover { background: #b91c1c; box-shadow: 0 4px 16px rgba(220,38,38,0.35); transform: translateY(-1px); }
.btn--outline  { background: transparent; color: #000000; border: 1.5px solid #E2E8F0; }
.btn--outline:hover { border-color: #000000; background: rgba(0,0,0,0.04); }
/* ghost on light bg (hero) = dark text; ghost on dark bg (cta) = white text */
.btn--ghost    { background: transparent; color: #000000; }
.btn--ghost:hover { background: rgba(0,0,0,0.06); }
/* nav outline on white bg */
.lp-nav .btn--outline { color: #000000; border-color: #CBD5E1; }
/* vehicle card Book now btn inherits primary — already red */
/* cta-banner btn—primary on dark bg is already red bg/white text — fine */
.btn--sm       { padding: 7px 14px; font-size: 13px; border-radius: 8px; }
.btn--lg       { font-size: 16px; padding: 14px 28px; border-radius: 12px; }
.btn--block    { width: 100%; justify-content: center; }
.btn--wide     { padding-left: 40px; padding-right: 40px; }
.btn-icon      { width: 16px; height: 16px; }

/* ── HERO ─────────────────────────────────────────────────────── */
.hero {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  padding: 96px 24px 64px;
  overflow: hidden;
}

.hero__bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.hero__grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(30,41,59,0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(30,41,59,0.04) 1px, transparent 1px);
  background-size: 48px 48px;
}

.hero__orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.35;
}
.hero__orb--1 {
  width: 600px; height: 600px;
  background: radial-gradient(circle, #dc2626 0%, transparent 70%);
  top: -200px; right: -150px;
}
.hero__orb--2 {
  width: 400px; height: 400px;
  background: radial-gradient(circle, #1e40af 0%, transparent 70%);
  bottom: -100px; left: -100px;
}

.hero__content {
  position: relative;
  max-width: 600px;
  z-index: 1;
}

.hero__badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(220,38,38,0.08);
  border: 1px solid rgba(220,38,38,0.2);
  color: #000000;
  font-size: 13px;
  font-weight: 600;
  padding: 6px 14px;
  border-radius: 9999px;
  margin-bottom: 24px;
}
.badge-icon { width: 14px; height: 14px; }

.hero__headline {
  font-size: clamp(40px, 6vw, 68px);
  font-weight: 800;
  line-height: 1.1;
  letter-spacing: -1.5px;
  color: var(--color-dark);
  margin-bottom: 20px;
}
.hero__headline--accent { color: #000000; }

.hero__sub {
  font-size: 18px;
  color: var(--color-muted);
  max-width: 480px;
  margin-bottom: 36px;
  line-height: 1.7;
}

.hero__cta-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 40px;
}

.hero__trust {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}

.trust-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--color-muted);
  font-weight: 500;
}
.trust-icon { width: 15px; height: 15px; color: var(--color-accent); }

/* floating demo card */
.hero__card-demo {
  position: absolute;
  right: max(5%, calc(50% - 560px + 32px));
  top: 50%;
  transform: translateY(-50%);
  z-index: 1;
}

.demo-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 20px;
  width: 280px;
  box-shadow: var(--shadow-hover);
  animation: float 4s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50%       { transform: translateY(-10px); }
}

.demo-card__header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 16px;
}
.demo-card__dot { width: 10px; height: 10px; border-radius: 50%; }
.demo-card__dot--red   { background: #ff5f57; }
.demo-card__dot--amber { background: #febc2e; }
.demo-card__dot--green { background: #28c840; }
.demo-card__title {
  margin-left: auto;
  font-size: 12px;
  font-weight: 600;
  color: var(--color-muted);
}

.demo-card__body {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 16px;
}

.demo-car-visual {
  width: 60px; height: 60px;
  background: linear-gradient(135deg, #1E293B 0%, #334155 100%);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.demo-car-icon { width: 28px; height: 28px; color: #fff; }

.demo-info { flex: 1; }
.demo-info__row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}
.demo-info__label { font-size: 11px; color: var(--color-muted); }
.demo-info__value { font-size: 12px; font-weight: 600; color: var(--color-dark); }
.demo-info__value--accent { color: #000000; }

.demo-card__status {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(34,197,94,0.08);
  border: 1px solid rgba(34,197,94,0.2);
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 11px;
  font-weight: 600;
  color: #000000;
}
.status-icon { width: 14px; height: 14px; color: #22c55e; }

/* ── LAYOUT HELPERS ───────────────────────────────────────────── */
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}

.section { padding: 96px 0; }
.section--light { background: var(--color-bg); }
.section--dark  { background: var(--color-dark); }

.section__header {
  text-align: center;
  margin-bottom: 56px;
}
.section__header--light .section__title { color: #000000; }

.section__title {
  font-size: clamp(28px, 4vw, 42px);
  font-weight: 800;
  letter-spacing: -0.8px;
  margin-bottom: 12px;
  line-height: 1.15;
}

.section__sub {
  font-size: 17px;
  color: var(--color-muted);
  max-width: 500px;
  margin: 0 auto;
}
.section__sub--muted { color: #000000; }

/* ── VEHICLES GRID ───────────────────────────────────────────── */
.vehicles-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 24px;
}

.vehicle-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 28px;
  box-shadow: var(--shadow-card);
  transition: transform var(--transition), box-shadow var(--transition);
}
.vehicle-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-hover);
}

.vehicle-card__icon-wrap {
  width: 52px; height: 52px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}
.vehicle-card--blue  .vehicle-card__icon-wrap { background: rgba(59,130,246,0.1); }
.vehicle-card--red   .vehicle-card__icon-wrap { background: rgba(220,38,38,0.1); }
.vehicle-card--amber .vehicle-card__icon-wrap { background: rgba(245,158,11,0.1); }

.vehicle-card__icon { width: 26px; height: 26px; }
.vehicle-card--blue  .vehicle-card__icon { color: #3b82f6; }
.vehicle-card--red   .vehicle-card__icon { color: var(--color-accent); }
.vehicle-card--amber .vehicle-card__icon { color: #f59e0b; }

.vehicle-card__name {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 6px;
  color: var(--color-dark);
}

.vehicle-card__desc {
  font-size: 14px;
  color: var(--color-muted);
  margin-bottom: 18px;
  line-height: 1.6;
}

.vehicle-card__features {
  list-style: none;
  padding: 0;
  margin-bottom: 24px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.vehicle-card__features li {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--color-dark);
  font-weight: 500;
}
.feature-check { width: 15px; height: 15px; color: #22c55e; flex-shrink: 0; }

.vehicle-card__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 20px;
  border-top: 1px solid var(--color-border);
}

.vehicle-card__price { display: flex; align-items: baseline; gap: 2px; }
.price-amount { font-size: 26px; font-weight: 800; color: var(--color-dark); }
.price-unit   { font-size: 13px; color: var(--color-muted); font-weight: 500; }

/* ── STEPS ───────────────────────────────────────────────────── */
.steps-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 32px;
}

.step-card {
  position: relative;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: var(--radius);
  padding: 32px;
  transition: background var(--transition), border-color var(--transition);
}
.step-card:hover {
  background: rgba(255,255,255,0.07);
  border-color: rgba(255,255,255,0.18);
}

.step-card__number {
  font-size: 11px;
  font-weight: 700;
  color: #000000;
  letter-spacing: 1px;
  margin-bottom: 16px;
  font-variant-numeric: tabular-nums;
}

.step-card__icon-wrap {
  width: 48px; height: 48px;
  background: rgba(220,38,38,0.12);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}
.step-card__icon { width: 24px; height: 24px; color: var(--color-accent); }

.step-card__title {
  font-size: 18px;
  font-weight: 700;
  color: #000000;
  margin-bottom: 10px;
}
.step-card__desc {
  font-size: 14px;
  color: #000000;
  line-height: 1.7;
}

/* ── FEATURES SPLIT ──────────────────────────────────────────── */
.features-split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 64px;
  align-items: center;
}

.features-split__copy .section__title { text-align: left; }
.features-split__body {
  font-size: 16px;
  color: var(--color-muted);
  margin: 12px 0 32px;
  line-height: 1.7;
}

.features-list {
  list-style: none;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.features-list__item {
  display: flex;
  gap: 14px;
  align-items: flex-start;
}

.features-list__icon-wrap {
  width: 40px; height: 40px;
  flex-shrink: 0;
  background: rgba(220,38,38,0.08);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.features-list__icon { width: 20px; height: 20px; color: var(--color-accent); }

.features-list__title { font-size: 15px; font-weight: 700; display: block; margin-bottom: 3px; }
.features-list__desc  { font-size: 13px; color: var(--color-muted); line-height: 1.6; }

/* dashboard mockup */
.dash-mockup {
  background: var(--color-dark);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: var(--radius);
  padding: 20px;
  box-shadow: var(--shadow-hover);
}

.dash-mockup__bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.dash-mockup__label { font-size: 13px; font-weight: 700; color: #000000; }
.dash-mockup__live  {
  display: flex; align-items: center; gap: 5px;
  font-size: 11px; font-weight: 600; color: #000000;
}
.live-dot {
  width: 7px; height: 7px;
  background: #22c55e;
  border-radius: 50%;
  animation: pulse 1.5s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%       { opacity: 0.5; transform: scale(0.85); }
}

.dash-mockup__row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}
.dash-mockup__pill {
  height: 10px;
  background: rgba(255,255,255,0.08);
  border-radius: 9999px;
  flex: 1;
}
.dash-mockup__badge {
  font-size: 10px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 9999px;
  white-space: nowrap;
}
.badge--green { background: rgba(34,197,94,0.15); color: #000000; }
.badge--amber { background: rgba(245,158,11,0.15); color: #000000; }

/* ── PRICING ─────────────────────────────────────────────────── */
.pricing-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 24px;
  margin-bottom: 32px;
}

.pricing-card {
  position: relative;
  background: var(--color-surface);
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius);
  padding: 32px;
  box-shadow: var(--shadow-card);
  transition: transform var(--transition), box-shadow var(--transition);
}
.pricing-card:hover { transform: translateY(-4px); box-shadow: var(--shadow-hover); }

.pricing-card--featured {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 1px var(--color-accent), var(--shadow-card);
}

.pricing-card__badge {
  position: absolute;
  top: -12px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--color-accent);
  color: #000000;
  font-size: 11px;
  font-weight: 700;
  padding: 4px 14px;
  border-radius: 9999px;
  white-space: nowrap;
  letter-spacing: 0.4px;
}

.pricing-card__icon-wrap {
  width: 48px; height: 48px;
  background: rgba(220,38,38,0.08);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}
.pricing-card__icon { width: 24px; height: 24px; color: var(--color-accent); }

.pricing-card__name {
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 12px;
}

.pricing-card__rate {
  display: flex;
  align-items: baseline;
  gap: 2px;
  margin-bottom: 12px;
}
.rate-dollar { font-size: 22px; font-weight: 800; color: var(--color-dark); }
.rate-amount { font-size: 42px; font-weight: 900; color: var(--color-dark); letter-spacing: -1px; font-variant-numeric: tabular-nums; }
.rate-unit   { font-size: 14px; color: var(--color-muted); font-weight: 500; }

.pricing-card__desc {
  font-size: 14px;
  color: var(--color-muted);
  margin-bottom: 20px;
  line-height: 1.6;
}

.pricing-card__includes {
  list-style: none;
  padding: 0;
  margin-bottom: 28px;
  display: flex;
  flex-direction: column;
  gap: 9px;
}
.pricing-card__includes li {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--color-dark);
  font-weight: 500;
}
.check-icon { width: 15px; height: 15px; color: #22c55e; flex-shrink: 0; }

.pricing-note {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--color-muted);
  text-align: center;
  justify-content: center;
}
.note-icon { width: 14px; height: 14px; flex-shrink: 0; }

/* ── CTA BANNER ──────────────────────────────────────────────── */
.cta-banner {
  position: relative;
  background: var(--color-dark);
  padding: 96px 24px;
  text-align: center;
  overflow: hidden;
}
.cta-banner__orb {
  position: absolute;
  width: 500px; height: 500px;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  background: radial-gradient(circle, rgba(220,38,38,0.18) 0%, transparent 65%);
  border-radius: 50%;
  pointer-events: none;
}

.cta-banner__headline {
  font-size: clamp(32px, 5vw, 52px);
  font-weight: 800;
  color: #000000;
  letter-spacing: -1px;
  margin-bottom: 16px;
}
.cta-banner__sub {
  font-size: 17px;
  color: #000000;
  margin-bottom: 36px;
}

/* ── FOOTER ──────────────────────────────────────────────────── */
.footer {
  background: var(--color-dark);
  border-top: 1px solid rgba(255,255,255,0.07);
  padding: 28px 24px;
}
.footer__inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}
.footer__brand { display: flex; align-items: center; gap: 8px; }
.footer__brand .brand-name { color: #000000; }
.footer__copy  { font-size: 13px; color: #000000; }

/* ── RESPONSIVE ──────────────────────────────────────────────── */
@media (max-width: 1024px) {
  .hero__card-demo { display: none; }
  .hero { padding-top: 80px; }
  .features-split {
    grid-template-columns: 1fr;
    gap: 40px;
  }
}

@media (max-width: 640px) {
  .lp-nav__links { display: none; }
  .hero__headline { letter-spacing: -0.8px; }
  .hero__cta-row { flex-direction: column; }
  .hero__cta-row .btn { width: 100%; justify-content: center; }
  .vehicles-grid, .steps-grid, .pricing-grid { grid-template-columns: 1fr; }
  .section { padding: 64px 0; }
}

/* ── ACCESSIBILITY ───────────────────────────────────────────── */
@media (prefers-reduced-motion: reduce) {
  .demo-card, .live-dot { animation: none; }
  *, *::before, *::after { transition-duration: 0.01ms !important; }
}

*:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 3px;
  border-radius: 4px;
}
</style>
