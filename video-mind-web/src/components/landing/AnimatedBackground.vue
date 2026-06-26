<template>
  <div class="animated-bg" aria-hidden="true">
    <div class="orb orb-1"></div>
    <div class="orb orb-2"></div>
    <div class="orb orb-3"></div>
    <div class="orb orb-4"></div>
    <div class="orb orb-5"></div>
  </div>
</template>

<style scoped>
.animated-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  background: linear-gradient(
    160deg,
    #f8fafc 0%,
    #eff3ff 25%,
    #f5f3ff 50%,
    #fdf2f8 75%,
    #f8fafc 100%
  );
  overflow: hidden;
}

.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  opacity: 0.55;
  animation: float 22s infinite ease-in-out;
  will-change: transform;
}

.orb-1 {
  width: 500px;
  height: 500px;
  background: radial-gradient(
    circle,
    rgba(129, 140, 248, 0.35) 0%,
    transparent 70%
  );
  top: -150px;
  left: -120px;
  animation-delay: 0s;
  animation-duration: 20s;
}

.orb-2 {
  width: 420px;
  height: 420px;
  background: radial-gradient(
    circle,
    rgba(167, 139, 250, 0.3) 0%,
    transparent 70%
  );
  top: 50%;
  right: -140px;
  animation-delay: -6s;
  animation-duration: 24s;
}

.orb-3 {
  width: 360px;
  height: 360px;
  background: radial-gradient(
    circle,
    rgba(244, 114, 182, 0.22) 0%,
    transparent 70%
  );
  bottom: -120px;
  left: 20%;
  animation-delay: -12s;
  animation-duration: 26s;
}

.orb-4 {
  width: 300px;
  height: 300px;
  background: radial-gradient(
    circle,
    rgba(99, 102, 241, 0.28) 0%,
    transparent 70%
  );
  top: 10%;
  left: 50%;
  animation-delay: -16s;
  animation-duration: 22s;
}

.orb-5 {
  width: 250px;
  height: 250px;
  background: radial-gradient(
    circle,
    rgba(139, 92, 246, 0.25) 0%,
    transparent 70%
  );
  top: 5%;
  right: 20%;
  animation-delay: -3s;
  animation-duration: 28s;
}

@keyframes float {
  0%,
  100% {
    transform: translate(0, 0) scale(1);
  }
  25% {
    transform: translate(60px, -50px) scale(1.1);
  }
  50% {
    transform: translate(-40px, 70px) scale(0.9);
  }
  75% {
    transform: translate(-65px, -30px) scale(1.05);
  }
}

@media (max-width: 768px) {
  .orb {
    filter: blur(70px);
    opacity: 0.4;
  }
  .orb-1 { width: 280px; height: 280px; }
  .orb-2 { width: 220px; height: 220px; }
  .orb-3 { width: 200px; height: 200px; }
  .orb-4 { width: 170px; height: 170px; }
  .orb-5 { width: 140px; height: 140px; }
}
</style>
