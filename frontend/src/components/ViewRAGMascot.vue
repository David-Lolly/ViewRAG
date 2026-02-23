<template>
  <div class="mascot-container">
    <!-- 充足的画布边界 -->
    <svg viewBox="-40 -80 480 540" xmlns="http://www.w3.org/2000/svg" :class="`status-${status}`">
        <defs>
            <linearGradient id="mainVGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#DD6645" />
                <stop offset="100%" stop-color="#A42714" />
            </linearGradient>

            <linearGradient id="headGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stop-color="#FFFFFF" />
                <stop offset="100%" stop-color="#FDF3E7" />
            </linearGradient>

            <!-- 滤镜区域足够大，防止切边 -->
            <filter id="dropShadow" x="-50%" y="-50%" width="200%" height="200%">
                <feDropShadow dx="0" dy="8" stdDeviation="6" flood-color="#8B1D0E" flood-opacity="0.25" />
            </filter>
            
            <filter id="lightShadow" x="-50%" y="-50%" width="200%" height="200%">
                <feDropShadow dx="2" dy="4" stdDeviation="3" flood-color="#A42714" flood-opacity="0.15" />
            </filter>

            <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>

            <clipPath id="v-clip">
                <path d="M 100 140 L 200 320 L 300 140" fill="none" stroke="#FFF" stroke-width="75" stroke-linecap="round" stroke-linejoin="round" />
            </clipPath>
        </defs>

        <!-- 底部地面阴影 -->
        <ellipse class="ground-shadow" cx="200" cy="400" rx="60" ry="10" fill="#8B1D0E" />

        <!-- === 主体弹性呼吸组 === -->
        <g class="mascot-physics">

            <!-- 1. V形主体 (去掉了左侧的文档，更加极简) -->
            <g class="body-main" filter="url(#dropShadow)">
                <path d="M 100 140 L 200 320 L 300 140" fill="none" stroke="url(#mainVGrad)" stroke-width="75" stroke-linecap="round" stroke-linejoin="round" />
                <path d="M 85 135 L 180 305" fill="none" stroke="#FFFFFF" stroke-width="8" stroke-linecap="round" opacity="0.25" />
                <path d="M 315 135 L 220 305" fill="none" stroke="#FFFFFF" stroke-width="8" stroke-linecap="round" opacity="0.1" />

                <!-- 内部电路节点 -->
                <g clip-path="url(#v-clip)" opacity="0.4">
                    <path d="M 110 180 L 140 230 L 180 230 L 200 270" fill="none" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />
                    <circle cx="110" cy="180" r="5" fill="#FFFFFF" />
                    <circle cx="200" cy="270" r="5" fill="#FFFFFF" />
                    <path d="M 280 200 L 250 240 L 210 240" fill="none" stroke="#FFFFFF" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
                    <circle cx="280" cy="200" r="4" fill="#FFFFFF" />
                    <circle cx="210" cy="240" r="4" fill="#FFFFFF" />
                </g>
            </g>

            <!-- 2. 右侧综合对话气泡 (定位在脸颊旁) -->
            <g transform="translate(290, 70)">
                <g class="prop-right" filter="url(#dropShadow)">
                    <!-- 气泡外壳 -->
                    <path d="M -35 -25 H 25 A 15 15 0 0 1 40 -10 V 15 A 15 15 0 0 1 25 30 H 10 L -5 45 L 0 30 H -35 A 15 15 0 0 1 -50 15 V -10 A 15 15 0 0 1 -35 -25 Z" fill="#FDF3E7" />
                    <path d="M -35 -25 H 25 A 15 15 0 0 1 40 -10 V 0 H -50 V -10 A 15 15 0 0 1 -35 -25 Z" fill="#FFFFFF" opacity="0.7" />
                    
                    <!-- 气泡内部内容：由 status 控制 v-show -->
                    <g transform="translate(-5, 0)">
                        <!-- idle：... -->
                        <g v-show="status === 'idle'" class="bubble-dots">
                            <circle cx="-15" cy="3" r="4" fill="#B22E1A" />
                            <circle cx="0" cy="3" r="4" fill="#B22E1A" />
                            <circle cx="15" cy="3" r="4" fill="#B22E1A" />
                        </g>

                        <!-- thinking：? -->
                        <g v-show="status === 'thinking'" class="bubble-question">
                            <g transform="translate(-2, 6) scale(0.65)">
                                <path d="M -10 -20 C -10 -35, 12 -35, 12 -20 C 12 -5, -2 -5, -2 5" fill="none" stroke="#DD6645" stroke-width="8" stroke-linecap="round" />
                                <circle cx="-2" cy="18" r="5" fill="#DD6645" />
                            </g>
                        </g>

                        <!-- answering：💡 -->
                        <g v-show="status === 'answering'" class="bubble-bulb">
                            <g transform="translate(-2, 12) scale(0.7)">
                                <g class="bulb-glow-rays" stroke="#FFD700" stroke-width="4" stroke-linecap="round" opacity="0.8">
                                    <line x1="0" y1="-38" x2="0" y2="-48" />
                                    <line x1="-25" y1="-15" x2="-35" y2="-15" />
                                    <line x1="25" y1="-15" x2="35" y2="-15" />
                                    <line x1="-18" y1="-32" x2="-25" y2="-39" />
                                    <line x1="18" y1="-32" x2="25" y2="-39" />
                                </g>
                                <g filter="url(#glow)">
                                    <circle cx="0" cy="-15" r="16" fill="#FFD700" />
                                    <rect x="-8" y="-1" width="16" height="10" rx="2" fill="#A42714" />
                                    <line x1="-6" y1="2" x2="6" y2="2" stroke="#FFFFFF" stroke-width="2" opacity="0.5"/>
                                    <line x1="-6" y1="6" x2="6" y2="6" stroke="#FFFFFF" stroke-width="2" opacity="0.5"/>
                                    <path d="M -8 -22 A 10 10 0 0 1 0 -28" fill="none" stroke="#FFFFFF" stroke-width="3" stroke-linecap="round" opacity="0.8"/>
                                </g>
                            </g>
                        </g>
                    </g>
                </g>
            </g>

            <!-- 3. 雷曼式悬浮小手 -->
            
            <!-- 左手 (完全锁定，不设任何额外动画，镜像对称右手的待机状态 15deg) -->
            <g transform="translate(70, 240) rotate(15)">
                <rect x="-12" y="-18" width="24" height="36" rx="12" fill="#DD6645" filter="url(#lightShadow)"/>
                <path d="M -6 -10 V 10" stroke="#FFFFFF" stroke-width="3" stroke-linecap="round" opacity="0.3"/>
            </g>

            <!-- 右手：thinking 时挠头循环，其余下垂 -->
            <g transform="translate(330, 240)">
                <g :class="status === 'thinking' ? 'arm-right-scratching' : 'arm-right-idle'" filter="url(#lightShadow)">
                    <rect x="-12" y="-18" width="24" height="36" rx="12" fill="#DD6645" />
                    <path d="M -6 -10 V 10" stroke="#FFFFFF" stroke-width="3" stroke-linecap="round" opacity="0.3"/>
                </g>
            </g>

        </g>
        <!-- === 主体弹性呼吸组 END === -->


        <!-- === 头部与表情组 === -->
        <g class="head-physics">
            
            <rect x="130" y="45" width="140" height="110" rx="40" fill="url(#headGrad)" stroke="url(#mainVGrad)" stroke-width="10" filter="url(#dropShadow)" />
            <path d="M 150 63 Q 200 53 250 63" fill="none" stroke="#FFFFFF" stroke-width="6" stroke-linecap="round" opacity="0.9" />
            
            <circle cx="160" cy="115" r="12" fill="#FF9A8B" opacity="0.5" />
            <circle cx="240" cy="115" r="12" fill="#FF9A8B" opacity="0.5" />

            <!-- 眼睛表情切换：由 status prop 控制 v-show -->
            <g transform="translate(0, 15)">

                <!-- idle：正常微笑 + 眨眼 -->
                <g v-show="status === 'idle'">
                    <g class="eyes-blink">
                        <circle cx="175" cy="85" r="8" fill="#4A180E" />
                        <circle cx="225" cy="85" r="8" fill="#4A180E" />
                        <circle cx="172" cy="82" r="2.5" fill="#FFFFFF" />
                        <circle cx="222" cy="82" r="2.5" fill="#FFFFFF" />
                    </g>
                    <path d="M 190 100 Q 200 110 210 100" fill="none" stroke="#4A180E" stroke-width="4.5" stroke-linecap="round" />
                </g>

                <!-- thinking：大小眼疑惑 -->
                <g v-show="status === 'thinking'">
                    <path d="M 168 85 L 182 85" fill="none" stroke="#4A180E" stroke-width="6" stroke-linecap="round" />
                    <circle cx="225" cy="83" r="10" fill="#4A180E" />
                    <circle cx="221" cy="80" r="3" fill="#FFFFFF" />
                    <path d="M 195 102 Q 200 100 205 103" fill="none" stroke="#4A180E" stroke-width="4" stroke-linecap="round" />
                </g>

                <!-- answering：弯眼开心 -->
                <g v-show="status === 'answering'">
                    <path d="M 168 88 Q 175 78 182 88" fill="none" stroke="#4A180E" stroke-width="5" stroke-linecap="round" />
                    <path d="M 218 88 Q 225 78 232 88" fill="none" stroke="#4A180E" stroke-width="5" stroke-linecap="round" />
                    <path d="M 188 100 Q 200 115 212 100" fill="none" stroke="#4A180E" stroke-width="4.5" stroke-linecap="round" />
                </g>

            </g>
        </g>
        <!-- === 头部与表情组 END === -->

    </svg>
  </div>
</template>

<script setup>
const props = defineProps({
  // 'idle' | 'thinking' | 'answering'
  status: { type: String, default: 'idle' },
});
</script>

<style scoped>
.mascot-container {
    width: 100%;
    max-width: 500px;
    height: auto;
    display: flex;
    justify-content: center;
    align-items: center;
}

/* ===== 常驻物理动画（所有状态都在呼吸） ===== */
.mascot-physics {
    transform-origin: 200px 320px;
    animation: squashStretch 3s ease-in-out infinite alternate;
}
.head-physics {
    transform-origin: 200px 100px;
    animation: headBob 3s ease-in-out infinite alternate;
}
.prop-right {
    animation: floatRight 4s ease-in-out infinite alternate-reverse;
}
.ground-shadow {
    animation: shadowPulse 3s ease-in-out infinite alternate;
    transform-origin: center;
    transform-box: fill-box;
}

/* ===== idle：眼睛眨眼 ===== */
.eyes-blink {
    transform-origin: center;
    transform-box: fill-box;
    animation: normalBlink 4s infinite;
}

/* ===== idle：气泡 dots 呼吸 ===== */
.bubble-dots {
    transform-origin: center;
    transform-box: fill-box;
    animation: dotsPulse 1.5s ease-in-out infinite alternate;
}

/* ===== thinking：问号摇摆 ===== */
.bubble-question {
    transform-origin: center;
    transform-box: fill-box;
    animation: questionWiggle 1s ease-in-out infinite alternate;
}

/* ===== answering：灯泡射线旋转 ===== */
.bulb-glow-rays {
    transform-origin: center;
    transform-box: fill-box;
    animation: raySpin 2s linear infinite;
}

/* ===== 右手：idle / answering 下垂 ===== */
.arm-right-idle {
    transform-origin: center;
    transform-box: fill-box;
    transform: translate(0, 0) rotate(-15deg);
    transition: transform 0.4s ease;
}

/* ===== 右手：thinking 持续挠头 ===== */
.arm-right-scratching {
    transform-origin: center;
    transform-box: fill-box;
    animation: scratchLoop 0.5s ease-in-out infinite alternate;
}

/* ===== Keyframes ===== */
@keyframes squashStretch {
    0%   { transform: translateY(0px) scaleX(1) scaleY(1); }
    100% { transform: translateY(-12px) scaleX(0.97) scaleY(1.03); }
}
@keyframes headBob {
    0%   { transform: translateY(0px) rotate(0deg); }
    100% { transform: translateY(4px) rotate(2deg); }
}
@keyframes floatRight {
    0%   { transform: translateY(0px) rotate(5deg); }
    100% { transform: translateY(-10px) rotate(8deg); }
}
@keyframes shadowPulse {
    0%   { transform: scale(1); opacity: 0.2; }
    100% { transform: scale(0.85); opacity: 0.08; }
}
@keyframes normalBlink {
    0%, 46%, 50%, 96%, 100% { transform: scaleY(1); }
    48%, 98%                 { transform: scaleY(0.1); }
}
@keyframes dotsPulse {
    0%   { opacity: 0.5; }
    100% { opacity: 1; }
}
@keyframes questionWiggle {
    0%   { transform: rotate(-8deg); }
    100% { transform: rotate(8deg); }
}
@keyframes raySpin {
    0%   { transform: rotate(0deg) scale(1); opacity: 0.6; }
    50%  { transform: rotate(45deg) scale(1.1); opacity: 1; }
    100% { transform: rotate(90deg) scale(1); opacity: 0.6; }
}
/* 持续挠头：在头侧上下微动 */
@keyframes scratchLoop {
    0%   { transform: translate(-30px, -108px) rotate(-28deg); }
    100% { transform: translate(-30px, -98px)  rotate(-18deg); }
}
</style>

/* ================= 物理循环动画 ================= */
.mascot-physics {
    transform-origin: 200px 320px;
    animation: squashStretch 3s ease-in-out infinite alternate;
}

.head-physics {
    transform-origin: 200px 100px;
    animation: headBob 3s ease-in-out infinite alternate;
}

/* 右侧对话气泡的整体悬浮 */
.prop-right {
    animation: floatRight 4s ease-in-out infinite alternate-reverse;
}

.ground-shadow {
    animation: shadowPulse 3s ease-in-out infinite alternate;
    transform-origin: center;
    transform-box: fill-box;
}

/* ================= 剧情循环动画 (12秒周期) ================= */
/* 右手的剧情动作 (挠头 -> 放下) */
.story-arm-right { 
    animation: storyRightArm 12s ease-in-out infinite; 
    transform-origin: center;
    transform-box: fill-box;
}

/* 眼睛状态切换 */
.eyes-normal { animation: fadeNormalEyes 12s infinite; }
.eyes-thinking { animation: fadeThinkingEyes 12s infinite; }
.eyes-happy { animation: fadeHappyEyes 12s infinite; }

.eyes-blink {
    transform-origin: center;
    transform-box: fill-box;
    animation: normalBlink 4s infinite;
}

/* ==== 方案A：气泡内部元素切换系统 ==== */
.story-dots {
    transform-origin: center;
    transform-box: fill-box;
    animation: fadeDots 12s infinite;
}

.story-question {
    transform-origin: center;
    transform-box: fill-box;
    animation: popQuestion 12s ease-in-out infinite;
}

.story-bulb {
    transform-origin: center;
    transform-box: fill-box;
    animation: popBulb 12s ease-in-out infinite;
}

.bulb-glow-rays {
    transform-origin: center;
    transform-box: fill-box;
    animation: raySpin 2s linear infinite;
}

/* ================= Keyframes 物理动画 ================= */
@keyframes squashStretch {
    0% { transform: translateY(0px) scaleX(1) scaleY(1); }
    100% { transform: translateY(-12px) scaleX(0.97) scaleY(1.03); }
}

@keyframes headBob {
    0% { transform: translateY(0px) rotate(0deg); }
    100% { transform: translateY(4px) rotate(2deg); }
}

@keyframes floatRight {
    0% { transform: translateY(0px) rotate(5deg); }
    100% { transform: translateY(-10px) rotate(8deg); }
}

@keyframes shadowPulse {
    0% { transform: scale(1); opacity: 0.2; }
    100% { transform: scale(0.85); opacity: 0.08; }
}

@keyframes normalBlink {
    0%, 46%, 50%, 96%, 100% { transform: scaleY(1); }
    48%, 98% { transform: scaleY(0.1); }
}

@keyframes raySpin {
    0% { transform: rotate(0deg) scale(1); opacity: 0.6; }
    50% { transform: rotate(45deg) scale(1.1); opacity: 1; }
    100% { transform: rotate(90deg) scale(1); opacity: 0.6; }
}

/* ================= Keyframes 12秒剧情大戏 ================= */

/* 极简版右手轨迹：待机 -> 挠头三下 -> 放下待机 */
@keyframes storyRightArm {
    0%, 20% { transform: translate(0, 0) rotate(-15deg); } /* 待机下垂 */
    28% { transform: translate(-30px, -110px) rotate(-30deg); } /* 抬手到脑门 */
    33% { transform: translate(-30px, -100px) rotate(-20deg); } /* 挠一下 */
    38% { transform: translate(-30px, -110px) rotate(-30deg); } /* 挠两下 */
    43% { transform: translate(-30px, -100px) rotate(-20deg); } /* 挠三下 */
    50%, 100% { transform: translate(0, 0) rotate(-15deg); } /* 5秒后放下，乖乖待机 */
}

@keyframes fadeNormalEyes {
    0%, 25% { opacity: 1; }
    28%, 77% { opacity: 0; }
    80%, 100% { opacity: 1; }
}
@keyframes fadeThinkingEyes {
    0%, 25% { opacity: 0; }
    28%, 48% { opacity: 1; }
    52%, 100% { opacity: 0; }
}
@keyframes fadeHappyEyes {
    0%, 48% { opacity: 0; }
    52%, 75% { opacity: 1; }
    78%, 100% { opacity: 0; }
}

@keyframes fadeDots {
    0%, 25% { opacity: 1; transform: scale(1); }
    28%, 75% { opacity: 0; transform: scale(0.5); }
    78%, 100% { opacity: 1; transform: scale(1); }
}

@keyframes popQuestion {
    0%, 25% { opacity: 0; transform: scale(0); }
    29% { opacity: 1; transform: scale(1.1) rotate(-10deg); }
