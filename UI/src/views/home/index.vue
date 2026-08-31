<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { storeToRefs } from "pinia";
import { useUserStore } from "@/pinia";
import { getTimeState } from "@/common/utils";
import { http } from "@/common/http";
import { t } from "@/common/languages";

defineOptions({ name: "Home" });

const router = useRouter();
const userStore = useUserStore();
const { userInfo } = storeToRefs(userStore);

const greeting = computed(() => {
  const hour = new Date().getHours();
  if (hour < 6) return t("_home.greetingNight");
  if (hour < 12) return t("_home.greetingMorning");
  if (hour < 18) return t("_home.greetingAfternoon");
  return t("_home.greetingEvening");
});

const timeState = ref("");
onMounted(() => {
  timeState.value = getTimeState();
  const now = new Date();
  const weekdays = [
    t("_home.weekday0"),
    t("_home.weekday1"),
    t("_home.weekday2"),
    t("_home.weekday3"),
    t("_home.weekday4"),
    t("_home.weekday5"),
    t("_home.weekday6"),
  ];
  todayDateInfo.value = {
    weekday: weekdays[now.getDay()],
    date: `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`,
    lunar: "",
    festival: "",
  };
  loadStats();
  fetchWeather();
});

const userRole = computed(() => {
  const roles = userInfo.value.roles || [];
  if (roles.includes("admin")) return "admin";
  if (roles.includes("teacher")) return "teacher";
  return "student";
});

const roleLabel = computed(() => {
  const map: Record<string, string> = {
    admin: t("_home.roleAdmin"),
    teacher: t("_home.roleTeacher"),
    student: t("_home.roleStudent"),
  };
  return map[userRole.value] || "";
});

interface StatItem {
  label: string;
  value: any;
  icon: string;
  color: string;
}
const quickStats = ref<StatItem[]>([
  { label: t("_home.statCourses"), value: 0, icon: "ep:notebook", color: "var(--tk-color-primary)" },
  { label: t("_home.statHours"), value: "0h", icon: "ep:timer", color: "var(--tk-color-success)" },
  { label: t("_home.statMessages"), value: "0", icon: "ep:chat-dot-round", color: "var(--tk-color-warning)" },
  { label: t("_home.statDays"), value: "0", icon: "ep:calendar", color: "var(--tk-color-secondary)" },
]);

const loadStats = async () => {
  try {
    const isAdmin = userRole.value === "admin" || userRole.value === "teacher";
    const res = await http.get<httpNs.Response<any>>(isAdmin ? "/admin/dashboard" : "/course/home-stats");
    const d = res.data || {};
    const hours = d.total_minutes != null ? Math.round((d.total_minutes || 0) / 60) + "h" : "—";
    quickStats.value = [
      {
        label: t("_home.statCourses"),
        value: d.course_count ?? d.active_course_count ?? 0,
        icon: "ep:notebook",
        color: "var(--tk-color-primary)",
      },
      { label: t("_home.statHours"), value: hours, icon: "ep:timer", color: "var(--tk-color-success)" },
      {
        label: t("_home.statMessages"),
        value: d.total_messages ?? 0,
        icon: "ep:chat-dot-round",
        color: "var(--tk-color-warning)",
      },
      {
        label: t("_home.statDays"),
        value: d.system_days ?? 0,
        icon: "ep:calendar",
        color: "var(--tk-color-secondary)",
      },
    ];
  } catch {
    /* keep defaults */
  }
};

const recentUsed = [
  {
    title: t("_home.actionCourses"),
    desc: t("_home.actionCoursesDesc"),
    icon: "ep:notebook",
    gradient: "linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)",
    route: "/course/dashboard",
  },
  {
    title: t("_home.actionChat"),
    desc: t("_home.actionChatDesc"),
    icon: "ep:chat-dot-round",
    gradient: "linear-gradient(135deg, #0891b2 0%, #06b6d4 100%)",
    route: "/course/dashboard",
  },
  {
    title: t("_home.actionStats"),
    desc: t("_home.actionStatsDesc"),
    icon: "ep:trend-charts",
    gradient: "linear-gradient(135deg, #16a34a 0%, #22c55e 100%)",
    route: "/course/learning-time",
  },
  {
    title: t("_home.actionEnroll"),
    desc: t("_home.actionEnrollDesc"),
    icon: "ep:plus",
    gradient: "linear-gradient(135deg, #dc2626 0%, #f97316 100%)",
    route: "/course/enroll",
  },
  {
    title: t("_home.actionSettings"),
    desc: t("_home.actionSettingsDesc"),
    icon: "ep:setting",
    gradient: "linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)",
    route: "/settings",
  },
];

interface WeatherInfo {
  temp: number | null;
  condition: string;
  icon: string;
  humidity: number | null;
  wind: string;
  city: string;
}

const WEATHER_CACHE_KEY = "home_weather_cache";

const weatherInfo = ref<WeatherInfo>({
  temp: null,
  condition: "",
  icon: "ep:cloudy",
  humidity: null,
  wind: "",
  city: "",
});
const weatherLoaded = ref(false);

const readWeatherCache = (): WeatherInfo | null => {
  try {
    const raw = localStorage.getItem(WEATHER_CACHE_KEY);
    return raw ? (JSON.parse(raw) as WeatherInfo) : null;
  } catch {
    return null;
  }
};

// ── WMO weather code → localized condition + icon ──
const weatherCodeToCondition = (code: number): { labelKey: string; icon: string } => {
  if (code === 0) return { labelKey: "_home.weatherClear", icon: "ep:sunny" };
  if (code >= 1 && code <= 3) return { labelKey: "_home.weatherPartlyCloudy", icon: "ep:cloudy" };
  if (code === 45 || code === 48) return { labelKey: "_home.weatherFog", icon: "ep:cloudy" };
  if (code >= 51 && code <= 67) return { labelKey: "_home.weatherRain", icon: "ep:cloudy" };
  if (code >= 71 && code <= 77) return { labelKey: "_home.weatherSnow", icon: "ep:cloudy" };
  if (code >= 80 && code <= 82) return { labelKey: "_home.weatherShowers", icon: "ep:cloudy" };
  if (code >= 85 && code <= 86) return { labelKey: "_home.weatherSnow", icon: "ep:cloudy" };
  if (code >= 95) return { labelKey: "_home.weatherThunder", icon: "ep:lightning" };
  return { labelKey: "_home.weatherPartlyCloudy", icon: "ep:cloudy" };
};

const degToCompass = (deg: number): string => {
  const dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
  return dirs[Math.round(deg / 45) % 8];
};

const getBrowserLocation = (): Promise<{ latitude: number; longitude: number }> =>
  new Promise((resolve, reject) => {
    if (!("geolocation" in navigator)) {
      reject(new Error("geolocation not supported"));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      pos => resolve({ latitude: pos.coords.latitude, longitude: pos.coords.longitude }),
      err => reject(err),
      { timeout: 6000, maximumAge: 600000 }
    );
  });

const getIpLocation = async (): Promise<{ latitude: number; longitude: number; city: string }> => {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 5000);
  try {
    const res = await fetch("https://ipwho.is/", { signal: controller.signal });
    if (!res.ok) throw new Error("ip lookup failed");
    const json = await res.json();
    if (!json.success || !json.latitude || !json.longitude) throw new Error("ip lookup empty");
    return { latitude: json.latitude, longitude: json.longitude, city: json.city || "" };
  } finally {
    clearTimeout(timer);
  }
};

const reverseGeocode = async (latitude: number, longitude: number): Promise<string> => {
  try {
    const url = `https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${latitude}&longitude=${longitude}&localityLanguage=zh`;
    const res = await fetch(url);
    if (!res.ok) return "";
    const json = await res.json();
    return json.city || json.locality || json.principalSubdivision || "";
  } catch {
    return "";
  }
};

const fetchWeather = async () => {
  // 1. Local fallback: reuse last successful fetch (offline / degraded)
  const cached = readWeatherCache();
  if (cached) {
    weatherInfo.value = cached;
    weatherLoaded.value = true;
  }

  try {
    // 2. Locate: browser geolocation → IP fallback
    let latitude: number;
    let longitude: number;
    let city = "";
    try {
      const pos = await getBrowserLocation();
      latitude = pos.latitude;
      longitude = pos.longitude;
    } catch {
      const ip = await getIpLocation();
      latitude = ip.latitude;
      longitude = ip.longitude;
      city = ip.city;
    }

    // 3. Weather from Open-Meteo (free, no key, CORS-enabled)
    const params = new URLSearchParams({
      latitude: String(latitude),
      longitude: String(longitude),
      current: "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,wind_direction_10m",
      wind_speed_unit: "kmh",
      timezone: "auto",
    });
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 8000);
    const res = await fetch(`https://api.open-meteo.com/v1/forecast?${params}`, { signal: controller.signal });
    clearTimeout(timer);
    if (!res.ok) return;
    const json = await res.json();
    const current = json.current;
    if (!current) return;

    // 4. City name (reverse geocode when browser location was used)
    if (!city) {
      city = await reverseGeocode(latitude, longitude);
    }

    const { labelKey, icon } = weatherCodeToCondition(current.weather_code ?? 3);
    const windSpeed = current.wind_speed_10m != null ? Math.round(current.wind_speed_10m) : 0;
    const windDir = current.wind_direction_10m != null ? degToCompass(current.wind_direction_10m) : "";

    const info: WeatherInfo = {
      temp: current.temperature_2m ?? null,
      condition: t(labelKey),
      icon,
      humidity: current.relative_humidity_2m ?? null,
      wind: `${windDir} ${windSpeed}km/h`.trim(),
      city,
    };
    weatherInfo.value = info;
    weatherLoaded.value = true;
    try {
      localStorage.setItem(WEATHER_CACHE_KEY, JSON.stringify(info));
    } catch {
      /* ignore quota / private-mode errors */
    }
  } catch {
    /* network / timeout / denied — keep cached value or empty state */
  }
};

const todayDateInfo = ref({ weekday: "", date: "", lunar: "", festival: "" });

const navigateTo = (route: string) => {
  router.push(route);
};
</script>

<template>
  <div class="home-page">
    <!-- Welcome Hero -->
    <div class="welcome-hero">
      <div class="hero-bg" />
      <div class="hero-content">
        <div class="hero-left">
          <div class="hero-greeting">
            <span class="greeting-wave">{{ timeState }}</span>
            <h1 class="greeting-title">{{ greeting }}，{{ userInfo.username || $t("_home.defaultUser") }}</h1>
            <p class="greeting-sub">
              {{ $t("_home.welcomeBack") }}
              <span v-if="roleLabel" class="role-badge">{{ roleLabel }}</span>
            </p>
          </div>
          <div class="hero-actions">
            <el-button size="large" round class="btn-primary-hero" @click="navigateTo('/course/dashboard')">
              <Icon icon="ep:school" :size="18" />
              {{ $t("_home.goToCourses") }}
            </el-button>
            <el-button size="large" round class="btn-secondary" @click="navigateTo('/course/dashboard')">
              <Icon icon="ep:chat-dot-round" :size="18" />
              {{ $t("_home.startChat") }}
            </el-button>
          </div>
        </div>
        <div class="hero-right">
          <div class="hero-illustration">
            <div class="illus-circle illus-1" />
            <div class="illus-circle illus-2" />
            <div class="illus-circle illus-3" />
            <Icon icon="ep:school" :size="56" class="illus-icon" />
          </div>
        </div>
      </div>
    </div>

    <!-- Quick Stats -->
    <div class="stats-row">
      <div v-for="stat in quickStats" :key="stat.label" class="stat-card">
        <div class="stat-icon" :style="{ '--stat-color': stat.color }">
          <Icon :icon="stat.icon" :size="20" />
        </div>
        <div class="stat-body">
          <span class="stat-value">{{ stat.value }}</span>
          <span class="stat-label">{{ stat.label }}</span>
        </div>
      </div>
    </div>

    <!-- Main Content: Bento Grid -->
    <div class="home-grid">
      <!-- Recently Used -->
      <div class="grid-section grid-section-actions">
        <div class="section-header">
          <h2 class="section-title">{{ $t("_home.recentlyUsed") }}</h2>
        </div>
        <div class="actions-grid">
          <div v-for="action in recentUsed" :key="action.title" class="action-card" @click="navigateTo(action.route)">
            <div class="action-icon" :style="{ background: action.gradient }">
              <Icon :icon="action.icon" :size="22" color="#fff" />
            </div>
            <div class="action-info">
              <span class="action-title">{{ action.title }}</span>
              <span class="action-desc">{{ action.desc }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Weather & Date -->
      <div class="grid-section grid-section-weather">
        <div class="section-header">
          <h2 class="section-title">{{ $t("_home.weather") }}</h2>
        </div>
        <div class="weather-card">
          <div class="weather-main">
            <div class="weather-icon-wrap">
              <Icon :icon="weatherInfo.icon || 'ep:cloudy'" :size="40" />
            </div>
            <div class="weather-info">
              <span class="weather-temp">
                {{ weatherLoaded && weatherInfo.temp != null ? weatherInfo.temp + "°C" : "—" }}
              </span>
              <span class="weather-cond">
                {{ weatherLoaded ? weatherInfo.condition : $t("_home.weatherUnavailable") }}
              </span>
            </div>
          </div>
          <div class="weather-detail">
            <div class="weather-row">
              <span class="weather-label">{{ $t("_home.weatherCity") }}</span>
              <span>{{ weatherInfo.city || "—" }}</span>
            </div>
            <div class="weather-row">
              <span class="weather-label">{{ $t("_home.weatherHumidity") }}</span>
              <span>{{ weatherInfo.humidity != null ? weatherInfo.humidity + "%" : "—" }}</span>
            </div>
            <div class="weather-row">
              <span class="weather-label">{{ $t("_home.weatherWind") }}</span>
              <span>{{ weatherInfo.wind || "—" }}</span>
            </div>
          </div>
        </div>

        <div class="date-divider" />

        <div class="section-header">
          <h2 class="section-title">{{ $t("_home.todayDate") }}</h2>
        </div>
        <div class="date-card">
          <div class="date-weekday">{{ todayDateInfo.weekday }}</div>
          <div class="date-main">{{ todayDateInfo.date }}</div>
          <div class="date-lunar">{{ todayDateInfo.lunar }}</div>
        </div>
      </div>
    </div>

    <!-- Tips Banner -->
    <div class="tips-banner">
      <div class="tips-icon-wrap">
        <Icon icon="ep:info-filled" :size="20" color="var(--tk-color-primary)" />
      </div>
      <div class="tips-content">
        <span class="tips-title">{{ $t("_home.tipsTitle") }}</span>
        <span class="tips-text">{{ $t("_home.tipsContent") }}</span>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.home-page {
  padding: 4px 0;
}

// Welcome Hero
.welcome-hero {
  position: relative;
  border-radius: 16px;
  overflow: hidden;
  margin-bottom: 24px;
}

.hero-bg {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 40%, #a855f7 100%);
  z-index: 0;
}

.hero-content {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 36px 40px;
  gap: 32px;
}

.hero-left {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.hero-greeting {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.greeting-wave {
  font-size: 28px;
  line-height: 1;
  color: #fff;
}

.greeting-title {
  font-size: 26px;
  font-weight: 700;
  color: #fff;
  margin: 0;
  line-height: 1.3;
}

.greeting-sub {
  font-size: 15px;
  color: rgba(255, 255, 255, 0.8);
  margin: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.role-badge {
  display: inline-flex;
  align-items: center;
  padding: 1px 10px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
  font-size: 12px;
  font-weight: 500;
}

.hero-actions {
  display: flex;
  gap: 12px;

  .btn-primary-hero {
    background: #fff;
    border-color: #fff;
    color: #4f46e5;
    font-weight: 600;

    &:hover {
      background: rgba(255, 255, 255, 0.9);
      border-color: rgba(255, 255, 255, 0.9);
      color: #4338ca;
    }
  }

  .btn-secondary {
    background: rgba(255, 255, 255, 0.15);
    border: 1px solid rgba(255, 255, 255, 0.25);
    color: #fff;

    &:hover {
      background: rgba(255, 255, 255, 0.25);
      border-color: rgba(255, 255, 255, 0.35);
    }
  }
}

.hero-right {
  flex-shrink: 0;
}

.hero-illustration {
  position: relative;
  width: 140px;
  height: 140px;
  display: flex;
  align-items: center;
  justify-content: center;

  .illus-circle {
    position: absolute;
    border-radius: 50%;
    border: 2px solid rgba(255, 255, 255, 0.15);
  }

  .illus-1 {
    width: 140px;
    height: 140px;
  }

  .illus-2 {
    width: 100px;
    height: 100px;
    border-color: rgba(255, 255, 255, 0.25);
    animation: spin-slow 20s linear infinite;
  }

  .illus-3 {
    width: 60px;
    height: 60px;
    background: rgba(255, 255, 255, 0.12);
    border: none;
  }

  .illus-icon {
    position: relative;
    z-index: 1;
    color: rgba(255, 255, 255, 0.9);
  }
}

@keyframes spin-slow {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

// Stats Row
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 20px;
  background: var(--tk-surface-bg-color-box);
  border: 1px solid var(--tk-surface-border-color);
  border-radius: 12px;
  box-shadow: var(--tk-box-shadow-xs);
  transition: all 0.25s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: var(--tk-box-shadow-md);
  }
}

.stat-icon {
  --stat-color: var(--tk-color-primary);
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: color-mix(in srgb, var(--stat-color) 12%, transparent);
  color: var(--stat-color);
  flex-shrink: 0;
}

.stat-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--tk-gray-color-900);
  line-height: 1.2;
}

.stat-label {
  font-size: 13px;
  color: var(--tk-gray-color-500);
  white-space: nowrap;
}

// Home Grid
.home-grid {
  display: grid;
  grid-template-columns: 1.3fr 0.9fr 0.8fr;
  gap: 20px;
  margin-bottom: 20px;
}

.grid-section {
  background: var(--tk-surface-bg-color-box);
  border: 1px solid var(--tk-surface-border-color);
  border-radius: 12px;
  box-shadow: var(--tk-box-shadow-xs);
  padding: 24px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--tk-gray-color-900);
  margin: 0;
  padding-left: 12px;
  position: relative;

  &::before {
    content: "";
    position: absolute;
    left: 0;
    top: 2px;
    bottom: 2px;
    width: 3px;
    border-radius: 2px;
    background: linear-gradient(135deg, var(--tk-color-primary), var(--tk-color-success));
  }
}

// Actions Grid
.actions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}

.action-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px;
  border: 1px solid var(--tk-surface-border-color);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.25s ease;

  &:hover {
    border-color: var(--tk-color-primary);
    box-shadow: var(--tk-box-shadow-sm);
    transform: translateY(-1px);
  }
}

.action-icon {
  width: 42px;
  height: 42px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.action-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.action-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--tk-gray-color-900);
}

.action-desc {
  font-size: 12px;
  color: var(--tk-gray-color-500);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.action-time {
  font-size: 11px;
  color: var(--tk-gray-color-400);
  flex-shrink: 0;
}

// Activity List
.activity-list {
  display: flex;
  flex-direction: column;
}

.activity-item {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 12px 0;

  & + & {
    border-top: 1px solid var(--tk-surface-border-color);
  }
}

.activity-dot {
  --dot-color: var(--tk-color-primary);
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: color-mix(in srgb, var(--dot-color) 10%, transparent);
  color: var(--dot-color);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 1px;
}

.activity-body {
  flex: 1;
  min-width: 0;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.activity-text {
  font-size: 13px;
  color: var(--tk-gray-color-700);
  line-height: 1.5;
}

.activity-time {
  font-size: 12px;
  color: var(--tk-gray-color-400);
  flex-shrink: 0;
  white-space: nowrap;
}

// Tips Banner
.tips-banner {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 20px;
  background: color-mix(in srgb, var(--tk-color-primary) 5%, transparent);
  border: 1px solid color-mix(in srgb, var(--tk-color-primary) 15%, transparent);
  border-radius: 10px;
}

.tips-icon-wrap {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: color-mix(in srgb, var(--tk-color-primary) 12%, transparent);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.tips-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.tips-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--tk-gray-color-800);
}

.tips-text {
  font-size: 12px;
  color: var(--tk-gray-color-500);
}

// Weather & Date Widget
.weather-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.weather-main {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px 0;
}

.weather-icon-wrap {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}

.weather-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.weather-temp {
  font-size: 28px;
  font-weight: 700;
  color: var(--tk-gray-color-900);
  line-height: 1;
}

.weather-cond {
  font-size: 13px;
  color: var(--tk-gray-color-500);
}

.weather-detail {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
  background: var(--tk-surface-bg-color-page);
  border-radius: 8px;
}

.weather-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: var(--tk-gray-color-600);

  .weather-label {
    color: var(--tk-gray-color-400);
  }
}

.date-divider {
  height: 1px;
  background: var(--tk-surface-border-color);
  margin: 4px 0;
}

.date-card {
  text-align: center;
  padding: 8px 0 4px;
}

.date-weekday {
  font-size: 15px;
  font-weight: 600;
  color: var(--tk-color-primary);
  margin-bottom: 6px;
}

.date-main {
  font-size: 20px;
  font-weight: 700;
  color: var(--tk-gray-color-900);
  margin-bottom: 4px;
}

.date-lunar {
  font-size: 12px;
  color: var(--tk-gray-color-400);
}

// Responsive
@media (max-width: 768px) {
  .hero-content {
    flex-direction: column;
    padding: 28px 24px;
    text-align: center;
  }

  .hero-left {
    align-items: center;
  }

  .hero-actions {
    flex-direction: column;
    width: 100%;

    .el-button {
      width: 100%;
    }
  }

  .hero-illustration {
    width: 100px;
    height: 100px;

    .illus-1 {
      width: 100px;
      height: 100px;
    }
    .illus-2 {
      width: 72px;
      height: 72px;
    }
    .illus-3 {
      width: 44px;
      height: 44px;
    }

    .illus-icon {
      width: 40px;
      height: 40px;
    }
  }

  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }

  .home-grid {
    grid-template-columns: 1fr;
  }
}
</style>
