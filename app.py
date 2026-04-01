import streamlit as st
import datetime
from google import genai
from google.genai import types
import json
import os
import plotly.graph_objects as go
from streamlit_local_storage import LocalStorage

# 初始化 LocalStorage
localS = LocalStorage()

# 默认自动存档键名
SAVE_KEY = "liferpg_save_data"

def get_slot_key(slot_id):
    return f"liferpg_save_slot_{slot_id}"

def load_game(key=SAVE_KEY):
    # 从浏览器 localStorage 获取数据
    data_str = localS.getItem(key)
    if data_str and isinstance(data_str, str):
        try:
            return json.loads(data_str)
        except:
            return {}
    elif isinstance(data_str, dict):
        return data_str
    return {}

def save_game(key=SAVE_KEY, ls_key=None):
    if ls_key is None:
        ls_key = key
    keys_to_save = [
        "game_stage", "player_name", "real_skills", "real_exp", "real_level",
        "rpg_str", "rpg_agi", "rpg_int", "rpg_con", "rpg_wis", "rpg_cha",
        "player_hp", "player_max_hp", "monster", "battle_log", "records",
        "inventory", "pending_loot", "death_time", "potions", "daily_quests", "is_boss", "last_daily_guide_date",
        "in_battle", "battle_result", "win_streak", "round_num", "battle_rounds", "battle_story", "current_monster_hp", "battle_logs_current", "battle_used_items", "equipped_skills"
    ]
    data_to_save = {k: st.session_state[k] for k in keys_to_save if k in st.session_state}
    # 将数据存入浏览器 localStorage
    localS.setItem(ls_key, json.dumps(data_to_save, ensure_ascii=False))

def delete_game(key, ls_key=None):
    if ls_key is None:
        ls_key = key
    localS.setItem(ls_key, "")

# ==========================================
# 0. 初始化 Session State (记录日程表及状态管理)
# ==========================================
# 确保在第一次运行时设置基础状态，以防 load_game 耗时
if 'game_stage' not in st.session_state:
    st.session_state.game_stage = 'character_creation'

# 点击按钮加载本地存档的标志位
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False

# 现实属性初始化 (将变为动态字典)
if 'real_skills' not in st.session_state:
    # 格式: {"英文能力": {"level": 4, "sub_level": 1, "exp": 45, "description": "留学生水平"}}
    st.session_state.real_skills = {}

if 'real_exp' not in st.session_state:
    st.session_state.real_exp = 0
if 'real_level' not in st.session_state:
    st.session_state.real_level = 1
if 'rpg_str' not in st.session_state:
    st.session_state.rpg_str = 10 # 力量
if 'rpg_agi' not in st.session_state:
    st.session_state.rpg_agi = 10 # 敏捷
if 'rpg_int' not in st.session_state:
    st.session_state.rpg_int = 10 # 智力
if 'rpg_con' not in st.session_state:
    st.session_state.rpg_con = 10 # 体质 (决定血量)
if 'rpg_wis' not in st.session_state:
    st.session_state.rpg_wis = 10 # 感知/神识
if 'rpg_cha' not in st.session_state:
    st.session_state.rpg_cha = 10 # 魅力/机缘

# 玩家战斗状态
if 'player_name' not in st.session_state:
    st.session_state.player_name = "无名修士"
if 'player_hp' not in st.session_state:
    st.session_state.player_hp = 100
if 'player_max_hp' not in st.session_state:
    st.session_state.player_max_hp = 100

# 战斗相关初始化 (重构为动态怪物)
if 'monster' not in st.session_state:
    st.session_state.monster = {
        "name": "拖延症缝合怪",
        "level": 1,
        "hp": 100,
        "max_hp": 100,
        "defense": 5, # 防御力：如果用户的力量/智力不够高，打它就会刮痧
        "description": "一只由你过去未完成的计划缝合而成的低级恶魔。"
    }
if 'battle_log' not in st.session_state:
    st.session_state.battle_log = []

# 日程记录初始化
if 'records' not in st.session_state:
    st.session_state.records = [
        {"time": "2023-10-25 10:00", "action": "完成了一篇 500 字的英文日记", "result": "英文能力经验 +10"},
        {"time": "2023-10-25 14:30", "action": "阅读了 10 页 ESG 相关政策报告", "result": "ESG 行业知识经验 +15"}
    ]

# 肉鸽道具与开发者系统初始化
if 'inventory' not in st.session_state:
    st.session_state.inventory = []
if 'pending_loot' not in st.session_state:
    st.session_state.pending_loot = []
if 'death_time' not in st.session_state:
    st.session_state.death_time = None
if 'dev_op_loot' not in st.session_state:
    st.session_state.dev_op_loot = False

# 新增进阶玩法状态初始化
if 'potions' not in st.session_state:
    st.session_state.potions = []
if 'daily_quests' not in st.session_state:
    st.session_state.daily_quests = []
if 'is_boss' not in st.session_state:
    st.session_state.is_boss = False
if 'last_daily_guide_date' not in st.session_state:
    st.session_state.last_daily_guide_date = ''

# --- 战斗重构相关状态 ---
if 'in_battle' not in st.session_state:
    st.session_state.in_battle = False
if 'battle_result' not in st.session_state:
    st.session_state.battle_result = None  # 'win', 'lose', 'draw'
if 'win_streak' not in st.session_state:
    st.session_state.win_streak = 0
if 'round_num' not in st.session_state:
    st.session_state.round_num = 0
if 'battle_rounds' not in st.session_state:
    st.session_state.battle_rounds = []
if 'battle_story' not in st.session_state:
    st.session_state.battle_story = ""
if 'current_monster_hp' not in st.session_state:
    st.session_state.current_monster_hp = 0
if 'battle_logs_current' not in st.session_state:
    st.session_state.battle_logs_current = [] # 当前场次的实时日志
if 'battle_used_items' not in st.session_state:
    st.session_state.battle_used_items = []
if 'equipped_skills' not in st.session_state:
    st.session_state.equipped_skills = {'active': [None, None, None], 'passive': [None, None, None]} # 记录本场战斗中已使用的主动法宝

# ==========================================
# 0.5 初始化大模型客户端 (使用硅基流动 SiliconFlow 免费 API)
# ==========================================
import os
from openai import OpenAI

# 请在这里填入你申请到的 SiliconFlow API Key
DEEPSEEK_API_KEY = "sk-rveglkugyavpfvkpsdwjticmtbnlbqonisfcvyhnzfhtrpbp" 

# 硅基流动接口地址和模型名称
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.siliconflow.cn/v1"
)
MODEL_NAME = "deepseek-ai/DeepSeek-V3" # 硅基流动上对应的免费 DeepSeek V3 模型

# ==========================================
# 1. 页面基本配置 (Layout)
# ==========================================
# 设置页面为宽屏模式，并加上酷炫的网页标题和 Emoji
st.set_page_config(
    page_title="LifeRPG: 现实修真引擎",
    page_icon="⚔️",
    layout="wide"
)

# ==========================================
# 1.05 强制加载本地存档按钮
# ==========================================
# 由于 Streamlit 的运行机制，直接在初始化时调用 LocalStorage 会有延迟，需要加一个加载界面
if not st.session_state.data_loaded:
    st.title("🌌 LifeRPG 正在连接天地法则...")
    st.write("点击下方按钮，从你的浏览器神识中唤醒存档数据：")
    
    # 获取本地存档
    auto_save_data = load_game(SAVE_KEY)
    
    if st.button("✨ 唤醒神识 (加载游戏)"):
        if auto_save_data and isinstance(auto_save_data, dict) and "game_stage" in auto_save_data:
            for k, v in auto_save_data.items():
                st.session_state[k] = v
        st.session_state.data_loaded = True
        st.rerun()
    
    st.stop() # 停止渲染后续内容，直到数据加载完毕

# 注入一些自定义 CSS 来增强暗黑史诗感
st.markdown("""
<style>
    /* 战斗日志区域暗黑修真风格 */
    .battle-log {
        background-color: #1a1a1a;
        color: #d4af37; /* 暗金色字体，增加史诗感 */
        padding: 15px;
        border-radius: 8px;
        font-family: 'Courier New', Courier, monospace;
        border-left: 5px solid #8b0000; /* 暗红边框，暗示鲜血与战斗 */
        margin-bottom: 20px;
        max-height: 800px; /* 固定高度，增加滚动条 */
        overflow-y: auto;
    }
    /* 遭遇战标题颜色 */
    .encounter-title {
        color: #ff4b4b;
    }
    /* 调整下划线样式 */
    hr {
        border-top: 1px solid #333 !important;
    }
    /* 创角页面居中样式 */
    .creation-container {
        max-width: 800px;
        margin: 0 auto;
        padding: 40px 20px;
        text-align: center;
    }
    
    /* 右侧悬浮日志栏样式 */
    .right-sidebar-log {
        position: fixed;
        top: 60px; /* 避开顶部导航栏 */
        right: 0;
        width: 320px; /* 宽度适中 */
        height: calc(100vh - 60px);
        background-color: #111; /* 深色背景 */
        border-left: 2px solid #333;
        padding: 15px;
        overflow-y: auto;
        z-index: 999;
        box-shadow: -5px 0 15px rgba(0,0,0,0.5);
    }
    
    /* 日志内容文字样式 */
    .right-sidebar-log .log-entry {
        color: #d4af37;
        font-family: 'Courier New', Courier, monospace;
        font-size: 14px;
        margin-bottom: 10px;
        line-height: 1.4;
        border-bottom: 1px dashed #333;
        padding-bottom: 5px;
    }
    
    .right-sidebar-log h3 {
        color: #fff;
        margin-top: 0;
        border-bottom: 2px solid #8b0000;
        padding-bottom: 10px;
        font-size: 18px;
    }
    
    /* 为了不让右侧日志栏遮挡主内容，给主容器增加右边距 */
    .block-container {
        padding-right: 340px !important; 
    }
    
    /* 移动端适配：屏幕太小的时候隐藏右侧悬浮栏，或者改成底部显示 (暂时先简单处理) */
    @media (max-width: 1024px) {
        .right-sidebar-log {
            display: none;
        }
        .block-container {
            padding-right: 1rem !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1.1 侧边栏：存档管理与开发者通道
# ==========================================
with st.sidebar:
    st.header("💾 轮回之境 (存档管理)")
    
    with st.expander("打开/关闭存档面板", expanded=False):
        for slot in [1, 2, 3]:
            slot_key = get_slot_key(slot)
            slot_data = load_game(slot_key)
            has_save = bool(slot_data and isinstance(slot_data, dict) and "game_stage" in slot_data)
            
            if has_save:
                # 读取简要信息展示
                p_name = slot_data.get("player_name", "无名修士")
                p_level = slot_data.get("real_level", 1)
                st.markdown(f"**存档 {slot}** - {p_name} (Lv {p_level})")
                
                # 如果有存档，显示读取、覆盖、删除按钮
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    if st.button("读取", key=f"load_{slot}", help="读取此存档"):
                        # 清空当前 session_state 中除了 dev_op_loot 和 data_loaded 以外的游戏数据
                        keys_to_clear = [
                            "game_stage", "player_name", "real_skills", "real_exp", "real_level",
                            "rpg_str", "rpg_agi", "rpg_int", "rpg_con", "rpg_wis", "rpg_cha",
                            "player_hp", "player_max_hp", "monster", "battle_log", "records",
                            "inventory", "pending_loot", "death_time", "potions", "daily_quests", "is_boss", "last_daily_guide_date",
                            "in_battle", "battle_result", "win_streak", "round_num", "battle_rounds", "battle_story", "current_monster_hp", "battle_logs_current", "battle_used_items", "equipped_skills"
                        ]
                        for k in keys_to_clear:
                            if k in st.session_state:
                                del st.session_state[k]
                        # 载入新数据
                        for k, v in slot_data.items():
                            st.session_state[k] = v
                        # 同时覆盖自动存档
                        save_game(SAVE_KEY, ls_key=f"load_auto_{slot}")
                        st.success(f"已读取存档 {slot}！")
                        st.rerun()
                with col_b:
                    if st.button("覆盖", key=f"save_over_{slot}", help="覆盖此存档"):
                        save_game(slot_key, ls_key=f"save_over_ls_{slot}")
                        st.success(f"已覆盖存档 {slot}！")
                        st.rerun()
                with col_c:
                    if st.button("删除", key=f"del_{slot}", help="删除此存档"):
                        delete_game(slot_key, ls_key=f"del_ls_{slot}")
                        st.warning(f"已删除存档 {slot}。")
                        st.rerun()
            else:
                st.markdown(f"**存档 {slot}** - 空")
                # 如果没有存档，显示保存或从新开始
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("保存当前", key=f"save_new_{slot}"):
                        save_game(slot_key, ls_key=f"save_new_ls_{slot}")
                        st.success(f"游戏已保存至槽位 {slot}！")
                        st.rerun()
                with col_b:
                    if st.button("从新开始", key=f"new_game_{slot}"):
                        # 清空内存数据，直接回到创角阶段
                        keys_to_clear = [
                            "game_stage", "player_name", "real_skills", "real_exp", "real_level",
                            "rpg_str", "rpg_agi", "rpg_int", "rpg_con", "rpg_wis", "rpg_cha",
                            "player_hp", "player_max_hp", "monster", "battle_log", "records",
                            "inventory", "pending_loot", "death_time", "potions", "daily_quests", "is_boss", "last_daily_guide_date",
                            "in_battle", "battle_result", "win_streak", "round_num", "battle_rounds", "battle_story", "current_monster_hp", "battle_logs_current", "battle_used_items", "equipped_skills"
                        ]
                        for k in keys_to_clear:
                            if k in st.session_state:
                                del st.session_state[k]
                        st.session_state.game_stage = 'character_creation'
                        # 同时将这个初始状态保存到对应的槽位和自动存档中
                        save_game(slot_key, ls_key=f"save_{slot}")
                        save_game(SAVE_KEY, ls_key=f"save_auto_{slot}")
                        st.rerun()
            
            st.markdown("---")

    st.header("� 轮回转生")
    if st.button("💥 斩断因果 (重新开始)", type="primary", use_container_width=True, help="清除当前游戏进度，从头开始"):
        keys_to_clear = [
            "game_stage", "player_name", "real_skills", "real_exp", "real_level",
            "rpg_str", "rpg_agi", "rpg_int", "rpg_con", "rpg_wis", "rpg_cha",
            "player_hp", "player_max_hp", "monster", "battle_log", "records",
            "inventory", "pending_loot", "death_time", "potions", "daily_quests", "is_boss", "last_daily_guide_date",
            "in_battle", "battle_result", "win_streak", "round_num", "battle_rounds", "battle_story", "current_monster_hp", "battle_logs_current", "battle_used_items", "equipped_skills"
        ]
        for k in keys_to_clear:
            if k in st.session_state:
                del st.session_state[k]
        st.session_state.game_stage = 'character_creation'
        delete_game(SAVE_KEY, ls_key="global_delete_auto")
        st.rerun()

    st.markdown("---")
    st.header("�🛠️ 开发者通道")
    dev_pwd = st.text_input("输入密钥", type="password")
    if dev_pwd == "981115":
        st.success("开发者模式已解锁")
        st.session_state.dev_op_loot = st.toggle("开启：大道金榜 (无视等级掉落神装)", value=st.session_state.dev_op_loot)
        if st.button("✨ 逆转时空 (复活并满血)"):
            st.session_state.player_hp = st.session_state.player_max_hp
            st.session_state.death_time = None
            save_game(SAVE_KEY, ls_key="dev_revive")
            st.rerun()

    # ==========================================
    # 2. 路由逻辑：创角页面 vs 主游戏页面
    # ==========================================

# --- 新战斗系统辅助函数 ---
import random

def get_synergy_counts():
    synergy_counts = {}
    for slot_type in ['active', 'passive']:
        for item in st.session_state.get('equipped_skills', {}).get(slot_type, []):
            if item is not None and 'synergy' in item:
                syn = item['synergy']
                synergy_counts[syn] = synergy_counts.get(syn, 0) + 1
    return synergy_counts

def get_effective_max_hp():
    base_hp = st.session_state.player_max_hp
    syn_counts = get_synergy_counts()
    if syn_counts.get('体修', 0) >= 2:
        return int(base_hp * 1.3)
    return base_hp

def get_total_stats():
    stats = {
        'str': st.session_state.rpg_str,
        'agi': st.session_state.rpg_agi,
        'int': st.session_state.rpg_int,
        'con': st.session_state.rpg_con,
        'wis': st.session_state.rpg_wis,
        'cha': st.session_state.rpg_cha
    }
    equipped_passives = st.session_state.get('equipped_skills', {}).get('passive', [])
    for item in equipped_passives:
        if item is not None and item.get('type') == 'passive' and 'stat_bonus' in item:
            bonus = item['stat_bonus']
            stats['str'] += bonus.get('str', 0)
            stats['agi'] += bonus.get('agi', 0)
            stats['int'] += bonus.get('int', 0)
            stats['con'] += bonus.get('con', 0)
            stats['wis'] += bonus.get('wis', 0)
            stats['cha'] += bonus.get('cha', 0)
    # 天道[2] 全属性+5
    syn_counts = get_synergy_counts()
    if syn_counts.get('天道', 0) >= 2:
        for k in stats:
            stats[k] += 5
            
    # 确保属性不为负数
    for k in stats:
        stats[k] = max(1, stats[k])
    return stats

def generate_dynamic_monster():
    new_level = st.session_state.monster['level'] + 1 if 'monster' in st.session_state and st.session_state.monster else 1
    is_next_boss = (new_level % 10 == 0)
    st.session_state.is_boss = is_next_boss
    
    streak = st.session_state.get('win_streak', 0)
    streak_mod = 1.0 + min(streak * 0.1, 1.0)
    
    base_hp = 50 + (new_level * 20)
    base_atk = 10 + (new_level * 5)
    base_def = 5 + (new_level * 3)
    
    new_max_hp = int(base_hp * streak_mod * (3 if is_next_boss else 1))
    new_atk = int(base_atk * streak_mod * (2 if is_next_boss else 1))
    new_def = int(base_def * streak_mod * (1.5 if is_next_boss else 1))
    
    monster_type = "【天劫心魔】" if is_next_boss else "普通妖兽"
    monster_prompt = f"生成一只《凡人修仙传》风格的修仙妖兽。等级 {new_level} 级。类型：{monster_type}。返回纯JSON：{{\"name\": \"妖兽名字\", \"description\": \"背景描述\"}}"
    
    try:
        m_res = client.chat.completions.create(
            model=MODEL_NAME, messages=[{"role": "user", "content": monster_prompt}], response_format={ "type": "json_object" }
        )
        m_text = m_res.choices[0].message.content.strip()
        if m_text.startswith("```json"): m_text = m_text[7:]
        if m_text.startswith("```"): m_text = m_text[3:]
        if m_text.endswith("```"): m_text = m_text[:-3]
        import json
        m_data = json.loads(m_text)
        new_name = m_data.get("name", f"不知名妖兽(Lv{new_level})")
        new_desc = m_data.get("description", "深渊中孕育的魔物。")
    except:
        new_name = f"妖兽(Lv{new_level})"
        new_desc = "深渊中孕育的魔物。"
        
    st.session_state.monster = {
        "name": new_name, "level": new_level, "hp": new_max_hp, "max_hp": new_max_hp, 
        "defense": new_def, "attack": new_atk, "description": new_desc
    }
    st.session_state.current_monster_hp = new_max_hp

def generate_loot_local(is_boss):
    loot_level = st.session_state.real_level
    loot_prompt_level = "夺天地造化的灵宝" if loot_level > 6 else ("筑基期法器" if loot_level > 3 else "凡人兵器")
    
    # 天道[6] 必定掉落神装
    syn_counts = get_synergy_counts()
    if st.session_state.dev_op_loot or is_boss or syn_counts.get('天道', 0) >= 6: 
        loot_prompt_level = "先天至宝"
    
    # 根据品阶动态调整数值范围
    if loot_prompt_level == "先天至宝":
        stat_range = "20~50"
        power_range = "500~1000"
    elif loot_prompt_level == "夺天地造化的灵宝":
        stat_range = "10~25"
        power_range = "200~400"
    elif loot_prompt_level == "筑基期法器":
        stat_range = "4~10"
        power_range = "50~150"
    else:
        stat_range = "1~5"
        power_range = "10~30"

    loot_prompt = f"""生成3个修仙战利品。品阶：{loot_prompt_level}。
法宝必须分为两类：被动(passive) 或 主动(active)。只能二选一。

【被动法宝】提供常驻六维属性加成(str力量, agi敏捷, int智力, con体质, wis感知, cha魅力)。加成数值应在 {stat_range} 之间，可有正负。必须包含 stat_bonus 字段。
【主动法宝】在战斗中可主动点击释放，每场战斗仅限1次。必须包含 skill_effect 和 power(数值范围 {power_range}) 字段。'skill_effect' 必须是以下五种之一：
1. 'nuke' (飞剑/重击：造成巨额直接伤害)
2. 'vampire' (魔道血祭：造成伤害并吸血)
3. 'shield' (防御法宝：本回合免伤)
4. 'stun' (神识震慑：本回合怪物无法反击)
5. 'heal' (恢复法宝：瞬间恢复大量气血，不造成伤害)

特别注意：所有的法宝都必须额外包含一个 "synergy" 字段！
它的值必须从以下五种羁绊中选择一个最符合法宝风格的：["剑修", "魔道", "体修", "法修", "天道"]。

返回纯JSON格式：
{{
  "loot": [
    {{
      "name": "玄铁重剑", "description": "沉重无比", "type": "passive", "stat_bonus": {{"str": 10, "agi": -2}}, "synergy": "剑修"
    }},
    {{
      "name": "青元剑诀", "description": "凝聚剑气", "type": "active", "skill_effect": "nuke", "power": 300, "synergy": "法修"
    }}
  ]
}}
"""
    try:
        loot_res = client.chat.completions.create(
            model=MODEL_NAME, messages=[{"role": "user", "content": loot_prompt}], response_format={ "type": "json_object" }
        )
        l_text = loot_res.choices[0].message.content.strip()
        if l_text.startswith("```json"): l_text = l_text[7:]
        if l_text.startswith("```"): l_text = l_text[3:]
        if l_text.endswith("```"): l_text = l_text[:-3]
        import json
        st.session_state.pending_loot = json.loads(l_text).get("loot", [])
    except:
        st.session_state.pending_loot = [{"name": "神秘残片", "description": "散发微弱灵光", "type": "passive", "stat_bonus": {"str": 1}}]

def process_combat_round(action_type, item_idx=None):
    stats = get_total_stats()
    p_str = stats['str']
    p_agi = stats['agi']
    p_int = stats['int']
    p_con = stats['con']
    
    m_atk = st.session_state.monster.get('attack', st.session_state.monster.get('defense', 5) * 2)
    m_def = st.session_state.monster.get('defense', 5)
    
    log_entry = f"【第{st.session_state.round_num}回合】 "
    monster_can_attack = True
    player_has_shield = False
    
    # 1. 玩家行动结算
    p_dmg_dealt = 0
    if action_type == "attack":
        is_crit = random.random() < min(p_agi / 100.0, 0.5) + extra_crit
        actual_m_def = 0 if p_ignore_def_phys else m_def
        base_dmg = max(1, p_str * 2 - actual_m_def)
        # 剑修[2] 攻击+15%
        if syn_counts.get('剑修', 0) >= 2: base_dmg = int(base_dmg * 1.15)
        dmg = int(base_dmg * (2.0 if is_crit else 1.0))
        # 剑修[6] 额外剑气斩
        if syn_counts.get('剑修', 0) >= 6:
            extra_dmg = max(1, int(p_str * 0.8))
            dmg += extra_dmg
            log_entry += f"【剑修】触发剑气斩，附加 {extra_dmg} 点伤害！"
            
        st.session_state.current_monster_hp = max(0, st.session_state.current_monster_hp - dmg)
        log_entry += f"你发起强攻{'，触发暴击！' if is_crit else '，'}造成 {dmg} 点伤害。"
        p_dmg_dealt = dmg
        
    elif action_type == "heal":
        if st.session_state.potions:
            potion = st.session_state.potions.pop(0)
            heal = potion.get('heal', 30)
            st.session_state.player_hp = min(get_effective_max_hp(), st.session_state.player_hp + heal)
            log_entry += f"你服用了【{potion['name']}】，恢复 {heal} 气血。"
        else:
            log_entry += "你伸手摸向行囊，却发现没有丹药了！"
            
    elif action_type == "spell":
        actual_m_def = 0 if p_ignore_def_magic else int(m_def * 0.5)
        dmg = max(1, p_int * 2 - actual_m_def)
        # 法修[2] 术法伤害+20%
        if syn_counts.get('法修', 0) >= 2: dmg = int(dmg * 1.2)
        # 法修[6] 双重施法
        if syn_counts.get('法修', 0) >= 6:
            dmg *= 2
            log_entry += f"【法修】触发双重施法！"
            
        st.session_state.current_monster_hp = max(0, st.session_state.current_monster_hp - dmg)
        log_entry += f"你施展术法，造成 {dmg} 点伤害。"
        p_dmg_dealt = dmg
    elif action_type == "equipped_active" and item_idx is not None:
        item = st.session_state.equipped_skills['active'][item_idx]
        st.session_state.battle_used_items.append(item['name'])
        effect = item.get('skill_effect', 'nuke')
        power = item.get('power', 20)
        
        log_entry += f"你祭出法宝【{item['name']}】！"
        if effect == 'nuke':
            dmg = max(1, power + p_int - int(m_def * 0.3))
            st.session_state.current_monster_hp = max(0, st.session_state.current_monster_hp - dmg)
            log_entry += f"法宝爆发出毁灭威能，造成 {dmg} 点伤害。"
        elif effect == 'vampire':
            dmg = max(1, power + p_int - int(m_def * 0.5))
            heal = int(dmg * 0.5)
            st.session_state.current_monster_hp = max(0, st.session_state.current_monster_hp - dmg)
            st.session_state.player_hp = min(st.session_state.player_max_hp, st.session_state.player_hp + heal)
            log_entry += f"魔光汲取了妖兽 {dmg} 点气血，反哺自身 {heal} 点气血。"
        elif effect == 'shield':
            player_has_shield = True
            log_entry += f"一道坚不可摧的屏障护住了你，本回合免疫妖兽伤害。"
        elif effect == 'stun':
            monster_can_attack = False
            dmg = max(1, int(power * 0.5))
            st.session_state.current_monster_hp = max(0, st.session_state.current_monster_hp - dmg)
            log_entry += f"强大的神识震慑了妖兽，造成 {dmg} 点伤害，妖兽本回合无法动弹！"
        elif effect == 'heal':
            heal = power + p_int
            st.session_state.player_hp = min(get_effective_max_hp(), st.session_state.player_hp + heal)
            log_entry += f"浓郁的生机涌入体内，瞬间恢复了 {heal} 点气血。"
            
    # 魔道[2] 吸血
    if p_dmg_dealt > 0 and syn_counts.get('魔道', 0) >= 2:
        lifesteal = max(1, int(p_dmg_dealt * 0.2))
        st.session_state.player_hp = min(get_effective_max_hp(), st.session_state.player_hp + lifesteal)
        log_entry += f"【魔道】汲取了 {lifesteal} 点气血。"
            
    # 2. 妖兽反击结算
    if st.session_state.current_monster_hp > 0 and monster_can_attack:
        if player_has_shield:
            log_entry += " 妖兽疯狂反扑，却被法宝/体修屏障完全挡下！"
            st.session_state.has_shield = False # 破盾
        else:
            is_dodge = random.random() < min(p_agi / 200.0, 0.4) + extra_dodge
            if is_dodge:
                log_entry += " 妖兽反扑，被你灵巧闪避！"
            else:
                m_dmg = max(1, m_atk - int(p_con * 0.5))
                m_dmg = int(m_dmg * p_dmg_reduce) # 魔道[4]减伤
                st.session_state.player_hp = max(0, st.session_state.player_hp - m_dmg)
                log_entry += f" 妖兽反击，对你造成 {m_dmg} 点伤害。"
                
                # 体修[6] 受到伤害反弹
                if syn_counts.get('体修', 0) >= 6:
                    reflect_dmg = max(1, int(m_dmg * 0.5))
                    st.session_state.current_monster_hp = max(0, st.session_state.current_monster_hp - reflect_dmg)
                    log_entry += f"【体修】反弹了 {reflect_dmg} 点伤害！"
                    
    # 魔道[6] 满血复活 (每场战斗限1次)
    if st.session_state.player_hp <= 0 and syn_counts.get('魔道', 0) >= 6 and not st.session_state.get('has_revived', False):
        st.session_state.player_hp = get_effective_max_hp()
        st.session_state.has_revived = True
        log_entry += "【魔道】真血沸腾！你从死亡边缘满血重生！"
            
    st.session_state.battle_logs_current.append(log_entry)
    st.session_state.battle_rounds.append(log_entry)
    st.session_state.round_num += 1
    
    # Check battle end
    if st.session_state.player_hp <= 0 and st.session_state.current_monster_hp <= 0:
        st.session_state.battle_result = "同归于尽"
    elif st.session_state.player_hp <= 0:
        st.session_state.battle_result = "战败"
    elif st.session_state.current_monster_hp <= 0:
        st.session_state.battle_result = "战胜"

def end_battle_cleanup(viewed_story=False):
    res = st.session_state.battle_result
    is_boss = st.session_state.get('is_boss', False)
    
    if not viewed_story:
        # 简单战报
        if res == "战胜":
            st.session_state.battle_log.insert(0, f"[大捷] 🎊 你斩杀了【{st.session_state.monster['name']}】！")
        elif res == "战败":
            st.session_state.battle_log.insert(0, f"[重伤] 🩸 你不敌【{st.session_state.monster['name']}】。")
        elif res == "同归于尽":
            st.session_state.battle_log.insert(0, f"[同归于尽] 💀 你与【{st.session_state.monster['name']}】玉石俱焚！")
            
    if res == "战胜":
        st.session_state.win_streak += 1
        generate_loot_local(is_boss)
        generate_dynamic_monster()
    elif res == "战败":
        st.session_state.win_streak = 0
        st.session_state.death_time = __import__('datetime').datetime.now().isoformat()
        if is_boss:
            st.session_state.real_exp = max(0, st.session_state.real_exp - 50)
            st.session_state.battle_log.insert(0, f"[天道反噬] ⚡ 渡劫失败，修为倒退50点！")
        # 怪物恢复满血
        st.session_state.current_monster_hp = st.session_state.monster['max_hp']
    elif res == "同归于尽":
        st.session_state.win_streak = 0
        st.session_state.death_time = __import__('datetime').datetime.now().isoformat()
        generate_loot_local(is_boss)
        generate_dynamic_monster()
        
    st.session_state.in_battle = False
    st.session_state.battle_result = None
    st.session_state.battle_logs_current = []
    st.session_state.battle_rounds = []
    st.session_state.round_num = 0
    st.session_state.battle_used_items = []
    save_game(SAVE_KEY, ls_key="battle_end")
    st.rerun()

# ==========================================
if st.session_state.game_stage == 'character_creation':
    # ------------------------------------------
    # 阶段一：创角页面 (Character Creation)
    # ------------------------------------------
    st.markdown('<div class="creation-container">', unsafe_allow_html=True)
    st.title("🌌 降生深渊：铸造你的现实道标")
    st.markdown("---")
    st.write("欢迎来到 LifeRPG。在踏入命运深渊之前，系统需要了解你目前的**现实能力底蕴**。")
    st.write("请用一段话描述你自己目前的技能和水平，AI 将为你自动生成初始的能力树。")
    st.info("💡 示例：我是一名大学生，英语过了六级，平时喜欢健身，最近在学习 Python 编程，对历史也比较感兴趣。")
    
    with st.form("creation_form"):
        player_name = st.text_input("你的尊号 / 角色名", value="无名修士", placeholder="输入你在修仙界的名号...")
        user_intro = st.text_area("你的自我介绍", height=150, placeholder="在这里写下你的自我介绍...")
        submitted_intro = st.form_submit_button("✨ 凝聚真身 (开始生成能力树)")
        
        if submitted_intro:
            if not user_intro.strip():
                st.warning("⚠️ 请先写下你的自我介绍，否则无法凝聚真身！")
            else:
                st.session_state.player_name = player_name.strip() or "无名修士"
                with st.spinner("✨ 诸天星辰正在为你演算命格..."):
                    try:
                        creation_prompt = """你是一个现实修真 RPG 游戏引擎的创角系统。
请根据用户的自我介绍，提取出他目前掌握的 3 到 5 个核心现实技能，并为每个技能评定初始的“大境界”（1-10级，1最弱，10最高）。
对于每个技能，你需要给出一个酷炫的修真风格或 RPG 风格的描述词。

请严格返回以下格式的纯 JSON 数据，不要包含任何 Markdown 标记：
{
    "skills": {
        "技能名称1": {"level": 整数1到10, "sub_level": 1, "exp": 0, "description": "技能的酷炫描述", "title": "对应的境界称号，如：炼气初期/入门者"},
        "技能名称2": {"level": 整数1到10, "sub_level": 1, "exp": 0, "description": "技能的酷炫描述", "title": "对应的境界称号"}
    },
    "base_stats": {
        "rpg_str": 力量初始值(10-20),
        "rpg_agi": 敏捷初始值(10-20),
        "rpg_int": 智力初始值(10-20),
        "rpg_con": 体质初始值(10-20),
        "rpg_wis": 神识感知初始值(10-20),
        "rpg_cha": 机缘魅力初始值(10-20)
    },
    "inventory": [
        {"name": "初始道具名1", "description": "符合现实隐喻的修仙道具描述，如'厚重的像砖头的英语词典，砸人极痛'"},
        {"name": "初始道具名2", "description": "符合现实隐喻的修仙道具描述"}
    ]
}"""
                        response = client.chat.completions.create(
                            model=MODEL_NAME,
                            messages=[
                                {"role": "system", "content": creation_prompt},
                                {"role": "user", "content": f"我的自我介绍是：{user_intro}"}
                            ],
                            response_format={ "type": "json_object" }
                        )
                        
                        result_text = response.choices[0].message.content.strip()
                        if result_text.startswith("```json"):
                            result_text = result_text[7:]
                        if result_text.startswith("```"):
                            result_text = result_text[3:]
                        if result_text.endswith("```"):
                            result_text = result_text[:-3]
                            
                        creation_data = json.loads(result_text)
                        
                        # 更新状态
                        st.session_state.real_skills = creation_data.get("skills", {})
                        
                        base_stats = creation_data.get("base_stats", {})
                        st.session_state.rpg_str = base_stats.get("rpg_str", 10)
                        st.session_state.rpg_agi = base_stats.get("rpg_agi", 10)
                        st.session_state.rpg_int = base_stats.get("rpg_int", 10)
                        st.session_state.rpg_con = base_stats.get("rpg_con", 10)
                        st.session_state.rpg_wis = base_stats.get("rpg_wis", 10)
                        st.session_state.rpg_cha = base_stats.get("rpg_cha", 10)
                        
                        # 根据体质初始化血量 (1体质 = 10血量)
                        st.session_state.player_max_hp = st.session_state.rpg_con * 10
                        st.session_state.player_hp = st.session_state.player_max_hp
                        
                        # 初始化初始道具
                        st.session_state.inventory = creation_data.get("inventory", [])
                        
                        # 切换到游玩阶段
                        st.session_state.game_stage = 'playing'
                        save_game()
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"创角失败: {str(e)}")
    
    st.markdown('</div>', unsafe_allow_html=True)

else:
    # ------------------------------------------
    # 阶段二：主游戏页面 (Main Game UI)
    # ------------------------------------------
    # 页面主标题
    st.title("⚔️ LifeRPG: 现实修真引擎")

    # ==========================================
    # 1.5 游戏介绍 (Game Introduction)
    # ==========================================
    with st.expander("📖 游戏指南：如何开启你的现实修真之路？"):
        st.markdown("""
        **LifeRPG** 是一款将现实努力转化为游戏属性的自我提升引擎。
        
        **【玩法核心】**：
        1. **⏳ 命运纺锤 (顶部)**：这是你的主要输入口。每天在这里记录你的现实成就（如“背了50个单词”、“跑了3公里”），AI 会自动为你结算经验、提升属性，甚至掉落丹药。
        2. **📜 现实道标 (左侧)**：展示你现实中各项技能的境界与等级，见证你的成长。同时可接取“天道悬赏”获取额外奖励。
        3. **⚔️ 命运深渊 (中间)**：使用你现实转化来的属性，点击“拔剑！生死斗法”挑战心魔妖兽。逢10级将遭遇不可逃避的天劫！
        4. **📜 日志 (右侧)**：这是一个常驻栏位，记录你所有的修炼感悟、境界突破、战斗推演与天道提示。
        
        **【核心特色：功法与羁绊系统】**：
        - 角色拥有 **3 个主动技能槽** 和 **3 个被动技能槽**。
        - 装备法宝与技能后，若带有相同标签，可激活**羁绊共鸣**（2件/4件/6件套）：
          - 🗡️ **剑修**：[2] 物理攻击+15% | [4] 无视妖兽护甲 | [6] 攻击时触发额外剑气斩
          - 🦇 **魔道**：[2] 攻击附带20%吸血 | [4] 低血量(30%以下)时受到伤害减半 | [6] 战斗中死亡可满血复活一次
          - 🛡️ **体修**：[2] 基础最大气血+30% | [4] 战斗开局获得绝对免伤护盾 | [6] 反弹受到的 50% 伤害
          - 🔮 **法修**：[2] 术法伤害+20% | [4] 术法无视魔抗 | [6] 触发双重施法（伤害翻倍）
          - 🌌 **天道**：[2] 基础六维全属性+5 | [4] 暴击率与闪避率各增加 15% | [6] 战斗胜利必定掉落【先天至宝】(最高品阶法宝)
        """)

    st.markdown("---")

    # ==========================================
    # 1.8 每日引导 (Daily Guide)
    # ==========================================
    today_str = datetime.date.today().isoformat()
    if st.session_state.get('last_daily_guide_date', '') != today_str:
        st.info("🌅 **每日引导**：新的一天开始了！修仙如逆水行舟，不进则退。请先在下方的【命运纺锤】记录今日的现实成就获取灵力，然后再去挑战心魔哦！")
        if st.button("✅ 开启今日修行"):
            st.session_state.last_daily_guide_date = today_str
            save_game(SAVE_KEY, ls_key="daily_guide")
            st.rerun()

    # ==========================================
    # 2. 移动端适配：标签页重构 (Tabs Layout)
    # ==========================================
    tab_combat, tab_cultivation, tab_inventory, tab_history = st.tabs([
        "⚔️ 征战 (首页)", "📜 修为 (属性)", "🎒 行囊 (物品)", "🗂️ 岁月 (日志)"
    ])

    # ------------------------------------------
    # Tab 1: 征战 (命运纺锤 + 命运深渊)
    # ------------------------------------------
    with tab_combat:
        st.header("⏳ 命运纺锤")
        st.caption("向命运纺锤献上你今日的现实成就，将其化为破局的力量吧！")
        
        with st.form("combat_action_form"):
            action_input = st.text_input(
                "你的现实成就", 
                placeholder="记录你今天的现实成就（例如：今天读了 20 页英文研报，写了 3000 字小说）...",
                label_visibility="collapsed"
            )
            submitted = st.form_submit_button("✨ 注入经验", use_container_width=True)
            
            if submitted:
                if action_input.strip() == "":
                    st.warning("⚠️ 纺锤空空如也，请先记录你的现实成就！")
                else:
                    with st.spinner("✨ 经验已注入，AI 正在演算战局..."):
                        try:
                            available_skills = list(st.session_state.real_skills.keys())
                            skills_str = ", ".join(available_skills) if available_skills else "通用经验"
                            
                            system_prompt = f"""你是一个融合了现实修真与《凡人修仙传》风格的文字RPG游戏引擎。 
用户会输入他今天在现实世界完成的修炼、日常行为，或者**对系统的管理指令（如要求拆分技能、重命名道标等）**。 

用户当前的专属技能树有：[{skills_str}]。

【指令分类与处理规则】（非常重要）
请仔细分析用户的输入，判断它是属于“修炼记录”还是“系统管理指令”。

情况 A：如果用户是普通的修炼记录（如：我今天背了10个日语单词）
1. 判断它最符合用户当前的哪个现实技能。如果不存在，请为他开辟一条新的技能分支（如：东瀛语之道）。
2. 根据努力量级评估 exp_gained (5-100)：微小(5-15)，中等(20-40)，较大(50-80)，重大突破(90-100)。
3. "system_action" 字段返回 "add_exp"。
4. 如果这是一个微小的努力(exp_gained < 20)，有几率掉落一颗恢复气血或增强状态的消耗品丹药。

情况 B：如果用户是系统管理指令（如截图中的：“异国语通包含了西班牙语与日语，我想让两个语言分开记录可以吗” 或 “帮我把健身改成炼体”）
1. 这不是一次修炼，不需要给经验！exp_gained 必须为 0。
2. "system_action" 字段返回 "modify_skills"。
3. 你必须在 "modify_instructions" 字段中，明确告诉系统要怎么修改现有的技能树。

你必须，且只能返回纯 JSON 格式的数据，不要包含任何 Markdown 标记！ 

JSON 格式必须包含以下字段： 
{{ 
"system_action": "必须是 'add_exp' 或 'modify_skills'",
"target_skill": "情况A时填匹配的技能名；情况B时填需要被修改或删除的旧技能名（如果没有则填空）",
"is_new_skill": true 或 false (仅情况A有效),
"new_skill_desc": "新技能的修真风格描述 (仅情况A有效)",
"exp_gained": 整数经验值 (情况B必须为0), 
"stat_up": "字符串，如 '智力 +2' (情况B必须为空字符串)",
"potion_drop": {{"name": "丹药名(如清心丹)", "heal": 20, "description": "恢复气血的描述"}} (可选，如果没有丹药掉落则返回 null 或省略此字段),
"modify_instructions": {{
    "action": "可以是 'rename'(重命名), 'split'(拆分), 'delete'(删除), 或 'none'",
    "new_skills": [
        {{"name": "新技能名1", "description": "修真风格描述1"}},
        {{"name": "新技能名2", "description": "修真风格描述2"}}
    ]
}},
"feedback_message": "给用户的一段话，修真风格。如果加经验就写获得了什么感悟；如果是修改系统，就写“天道已按你的意志重塑了道标”等"
}}"""
                            response = client.chat.completions.create(
                                model=MODEL_NAME,
                                messages=[
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user", "content": f"我今天的修炼成果是：{action_input}"}
                                ],
                                response_format={ "type": "json_object" }
                            )
                            
                            result_text = response.choices[0].message.content.strip()
                            if result_text.startswith("```json"): result_text = result_text[7:]
                            if result_text.startswith("```"): result_text = result_text[3:]
                            if result_text.endswith("```"): result_text = result_text[:-3]
                                
                            result_data = json.loads(result_text)
                            
                            system_action = result_data.get("system_action", "add_exp")
                            feedback_message = result_data.get("feedback_message", "")
                            
                            if system_action == "modify_skills":
                                instructions = result_data.get("modify_instructions", {})
                                action = instructions.get("action", "none")
                                target_skill = result_data.get("target_skill", "")
                                new_skills = instructions.get("new_skills", [])
                                
                                if action == "split" or action == "rename":
                                    if target_skill in st.session_state.real_skills:
                                        old_skill_data = st.session_state.real_skills.pop(target_skill)
                                        for ns in new_skills:
                                            st.session_state.real_skills[ns["name"]] = {
                                                "level": old_skill_data["level"],
                                                "sub_level": old_skill_data["sub_level"],
                                                "exp": old_skill_data["exp"],
                                                "description": ns["description"],
                                                "title": old_skill_data["title"]
                                            }
                                elif action == "delete":
                                    if target_skill in st.session_state.real_skills:
                                        del st.session_state.real_skills[target_skill]
                                        
                                st.session_state.battle_log.insert(0, f"[天道重塑] 🌌 {feedback_message}")
                                
                                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                                st.session_state.records.insert(0, {
                                    "time": now,
                                    "action": f"【指令】{action_input}",
                                    "result": "系统道标已重塑"
                                })
                                
                            else:
                                exp_gained = result_data.get("exp_gained", 10)
                                target_skill = result_data.get("target_skill", "通用经验")
                                is_new_skill = result_data.get("is_new_skill", False)
                                
                                if is_new_skill and target_skill not in st.session_state.real_skills:
                                    st.session_state.real_skills[target_skill] = {
                                        "level": 1,
                                        "sub_level": 1,
                                        "exp": 0,
                                        "description": result_data.get("new_skill_desc", "一条崭新的修真大道。"),
                                        "title": "初窥门径"
                                    }
                                    st.session_state.battle_log.insert(0, f"[顿悟] 🎇 你的行为引动了天地法则，开辟了新的道标：【{target_skill}】！")
        
                                if target_skill in st.session_state.real_skills:
                                    skill = st.session_state.real_skills[target_skill]
                                    skill['exp'] += exp_gained
                                    if skill['exp'] >= 100:
                                        levels_up = skill['exp'] // 100
                                        skill['exp'] = skill['exp'] % 100
                                        skill['sub_level'] += levels_up
                                        
                                        if skill['sub_level'] > 10:
                                            major_levels_up = skill['sub_level'] // 10
                                            skill['sub_level'] = skill['sub_level'] % 10
                                            if skill['sub_level'] == 0: 
                                                skill['sub_level'] = 10
                                                major_levels_up -= 1
                                            skill['level'] += major_levels_up
                                            
                                            title_prompt = f"修真者在【{target_skill}】这一道上突破到了第 {skill['level']} 大境界，请给他一个符合《凡人修仙传》风格的 4-6 字称号。只返回称号本身。"
                                            try:
                                                t_res = client.chat.completions.create(
                                                    model=MODEL_NAME,
                                                    messages=[{"role": "user", "content": title_prompt}]
                                                )
                                                skill['title'] = t_res.choices[0].message.content.strip()
                                            except:
                                                pass
                                                
                                            st.session_state.battle_log.insert(0, f"[突破] 🌌 你的【{target_skill}】突破到了 大境界 {skill['level']}阶 ({skill['title']})！")
                                        else:
                                            st.session_state.battle_log.insert(0, f"[精进] 🌟 你的【{target_skill}】提升到了 小境界 {skill['sub_level']}重！")
        
                                master_exp_gained = max(1, exp_gained // 2)
                                st.session_state.real_exp += master_exp_gained
                                if st.session_state.real_exp >= 100:
                                    st.session_state.real_level += 1
                                    st.session_state.real_exp -= 100
                                    st.session_state.battle_log.insert(0, f"[飞升] 👑 苍穹震动！【{st.session_state.player_name}】的境界提升到了 Lv {st.session_state.real_level}！")
                                    
                                stat_up = result_data.get("stat_up", "")
                                if "力量" in stat_up: st.session_state.rpg_str += int(''.join(filter(str.isdigit, stat_up)) or 1)
                                elif "敏捷" in stat_up: st.session_state.rpg_agi += int(''.join(filter(str.isdigit, stat_up)) or 1)
                                elif "智力" in stat_up: st.session_state.rpg_int += int(''.join(filter(str.isdigit, stat_up)) or 1)
                                elif "体质" in stat_up: 
                                    st.session_state.rpg_con += int(''.join(filter(str.isdigit, stat_up)) or 1)
                                    st.session_state.player_max_hp = st.session_state.rpg_con * 10
                                elif "感知" in stat_up: st.session_state.rpg_wis += int(''.join(filter(str.isdigit, stat_up)) or 1)
                                elif "魅力" in stat_up: st.session_state.rpg_cha += int(''.join(filter(str.isdigit, stat_up)) or 1)
                                    
                                heal_amount = int(st.session_state.player_max_hp * (0.2 + (exp_gained / 200.0)))
                                st.session_state.player_hp = min(st.session_state.player_max_hp, st.session_state.player_hp + heal_amount)
                                    
                                st.session_state.battle_log.insert(0, f"[修炼] {feedback_message} (气血恢复 {heal_amount} 点)")
                                
                                potion_drop = result_data.get("potion_drop")
                                if potion_drop and isinstance(potion_drop, dict) and "name" in potion_drop:
                                    st.session_state.potions.append(potion_drop)
                                    st.session_state.battle_log.insert(0, f"[炼丹] ⚗️ 天道感应到你的日常微小努力，赐下了一枚【{potion_drop.get('name', '神秘丹药')}】！")
                                    
                                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                                record_result = f"【{target_skill}】经验 +{exp_gained}, {stat_up}"
                                st.session_state.records.insert(0, {
                                    "time": now,
                                    "action": action_input,
                                    "result": record_result
                                })
                            
                        # 刷新页面以更新 UI
                            save_game(SAVE_KEY, ls_key="action_input")
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"API 调用或解析失败: {str(e)}")
                            st.info("原返回内容: " + result_text if 'result_text' in locals() else "无")

        st.markdown("---")
        st.header("⚔️ 命运深渊")
        
        can_fight = True
        if st.session_state.death_time:
            death_dt = datetime.datetime.fromisoformat(st.session_state.death_time)
            now = datetime.datetime.now()
            diff = now - death_dt
            if diff.total_seconds() < 24 * 3600:
                can_fight = False
                remaining = 24 * 3600 - diff.total_seconds()
                h = int(remaining // 3600)
                m = int((remaining % 3600) // 60)
                st.error(f"💀 本尊肉身重塑中，还需等待 {h}小时 {m}分钟...")
            else:
                st.session_state.death_time = None
                save_game(SAVE_KEY, ls_key="death_recover")
                
        if st.session_state.pending_loot:
            st.warning("🎁 发现战利品！请先处理战利品后才能继续探索。")
            with st.container():
                st.markdown("##### ✨ 选择你要收入囊中的道具")
                cols = st.columns(3)
                for idx, loot in enumerate(st.session_state.pending_loot):
                    with cols[idx]:
                        st.markdown(f"**{loot['name']}**")
                        st.caption(loot['description'])
                        if st.button(f"选择 {loot['name']}", key=f"loot_{idx}"):
                            if len(st.session_state.inventory) < 3:
                                st.session_state.inventory.append(loot)
                                st.session_state.pending_loot = []
                                save_game(SAVE_KEY, ls_key=f"loot_take_{idx}")
                                st.rerun()
                            else:
                                st.session_state.selected_loot = loot
                                st.rerun()
                
                if 'selected_loot' in st.session_state:
                    st.markdown("---")
                    st.write(f"你选择了 **{st.session_state.selected_loot['name']}**，但须弥芥子已满，请选择要替换的道具：")
                    replace_idx = st.selectbox("选择要替换的道具", range(len(st.session_state.inventory)), format_func=lambda x: st.session_state.inventory[x]['name'])
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("确认替换"):
                            st.session_state.inventory[replace_idx] = st.session_state.selected_loot
                            del st.session_state.selected_loot
                            st.session_state.pending_loot = []
                            save_game(SAVE_KEY, ls_key="loot_replace")
                            st.rerun()
                    with col_b:
                        if st.button("取消选择"):
                            del st.session_state.selected_loot
                            st.rerun()
                
                st.markdown("---")
                if st.button("🗑️ 放弃所有战利品", use_container_width=True):
                    st.session_state.pending_loot = []
                    if 'selected_loot' in st.session_state:
                        del st.session_state.selected_loot
                    save_game(SAVE_KEY, ls_key="loot_discard")
                    st.rerun()

        elif st.session_state.player_hp <= 0 and can_fight:
            st.error("⚠️ 你的气血已见底，强行出战必死无疑。请先通过【命运纺锤】进行现实修炼，恢复气血！")
        elif can_fight:
            monster = st.session_state.monster
            
            # --- 未在战斗中 ---
            if not st.session_state.in_battle:
                eff_hp = get_effective_max_hp()
                st.markdown(f"**气血 (HP)**: {st.session_state.player_hp} / {eff_hp}")
                st.progress(max(0.0, min(1.0, st.session_state.player_hp / eff_hp)))
                st.write("")
                
                if st.session_state.get('is_boss', False):
                    st.markdown(f"<h3 class='encounter-title'>⚡ 【天劫降临】 [Lv {monster['level']}] {monster['name']}</h3>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<h4 class='encounter-title'>🔥 当前遭遇：[Lv {monster['level']}] {monster['name']}</h4>", unsafe_allow_html=True)
                st.caption(f"*{monster['description']}* (威胁度: {monster.get('attack', 10) + monster.get('defense', 5)}) | 连胜: {st.session_state.get('win_streak', 0)}")
                
                # 初始怪血条
                if st.session_state.current_monster_hp == 0:
                    st.session_state.current_monster_hp = monster['max_hp']
                hp_ratio = max(0.0, st.session_state.current_monster_hp / monster['max_hp'])
                st.progress(hp_ratio, text=f"妖兽气血: {st.session_state.current_monster_hp}/{monster['max_hp']}")
                st.write("")
                
                if st.button("⚔️ 拔剑！生死斗法", use_container_width=True, type="primary"):
                    st.session_state.in_battle = True
                    st.session_state.battle_result = None
                    st.session_state.round_num = 1
                    st.session_state.battle_rounds = []
                    st.session_state.battle_logs_current = []
                    st.session_state.battle_used_items = []
                    st.session_state.current_monster_hp = monster['max_hp']
                    st.session_state.has_revived = False
                    st.session_state.has_shield = False
                    st.session_state.player_hp = min(st.session_state.player_hp, get_effective_max_hp())
                    save_game(SAVE_KEY, ls_key="battle_start")
                    st.rerun()
            
            # --- 战斗进行中 / 结算 ---
            else:
                st.markdown(f"<h4 style='color:#ff4b4b;'>⚔️ 战斗进行中 - 第 {st.session_state.round_num} 回合</h4>", unsafe_allow_html=True)
                
                c_p, c_m = st.columns(2)
                with c_p:
                    eff_hp = get_effective_max_hp()
                    st.markdown(f"**你 ({st.session_state.player_hp}/{eff_hp})**")
                    st.progress(max(0.0, min(1.0, st.session_state.player_hp / eff_hp)))
                with c_m:
                    st.markdown(f"**{monster['name']} ({st.session_state.current_monster_hp}/{monster['max_hp']})**")
                    st.progress(max(0.0, st.session_state.current_monster_hp / monster['max_hp']))
                
                st.write("")
                
                # 战斗日志窗口
                if st.session_state.battle_logs_current:
                    log_html = "<br>".join(st.session_state.battle_logs_current[-5:]) # 只显示最近5条
                    st.markdown(f"<div style='background:#111; padding:10px; border-left:3px solid #555; height:120px; overflow-y:auto; color:#ccc; font-size:14px;'>{log_html}</div>", unsafe_allow_html=True)
                st.write("")
                
                # 若战斗未结束，显示操作按钮
                if st.session_state.battle_result is None:
                    st.markdown("##### ⚡ 行动")
                    col_atk, col_spell, col_heal = st.columns(3)
                    with col_atk:
                        if st.button("🗡️ 强攻", use_container_width=True): 
                            process_combat_round("attack")
                            st.rerun()
                    with col_spell:
                        if st.button("✨ 术法", use_container_width=True): 
                            process_combat_round("spell")
                            st.rerun()
                    with col_heal:
                        if st.button(f"⚗️ 吃药 ({len(st.session_state.potions)})", use_container_width=True): 
                            process_combat_round("heal")
                            st.rerun()
                            
                    # 动态渲染已装备的主动技能/法宝
                    active_items = [(idx, item) for idx, item in enumerate(st.session_state.get('equipped_skills', {}).get('active', [])) if item is not None]
                    if active_items:
                        st.markdown("##### 🔮 祭出法宝")
                        item_cols = st.columns(len(active_items))
                        for col, (idx, item) in zip(item_cols, active_items):
                            with col:
                                is_used = item['name'] in st.session_state.get('battle_used_items', [])
                                btn_label = f"🚫 {item['name']} (已用)" if is_used else f"⚡ {item['name']}"
                                if st.button(btn_label, disabled=is_used, use_container_width=True, key=f"use_item_{idx}", help=item.get('description', '')):
                                    process_combat_round("equipped_active", item_idx=idx)
                                    st.rerun()
                
                # 战斗已分出胜负
                else:
                    st.markdown("---")
                    res = st.session_state.battle_result
                    if res == "战胜":
                        st.success(f"🎉 **大捷！你成功击杀了 {monster['name']}**")
                    elif res == "战败":
                        st.error(f"💀 **惨败！你不敌 {monster['name']}**")
                    elif res == "同归于尽":
                        st.warning(f"💥 **同归于尽！你与 {monster['name']} 玉石俱焚！**")
                        
                    c_view, c_cont = st.columns(2)
                    with c_view:
                        if st.button("📜 查看结果 (生成小说)", use_container_width=True, type="primary"):
                            with st.spinner("天地法则推演中..."):
                                prompt = f"""你是一个《凡人修仙传》风格的文字RPG说书人。
请根据以下【战斗过程摘要】与玩家的【法宝信息】，写一段150-250字的修仙战斗战报，不要写额外分析。
玩家：{st.session_state.player_name}
装备法宝：{', '.join([item['name'] for item in st.session_state.get('inventory', [])])}
妖兽：{monster['name']}
回合摘要：
{chr(10).join(st.session_state.battle_rounds)}
最终结局：{res}
(提示：请在描写中，明确体现出玩家的【装备法宝】在战斗中发挥的作用，不论是主动效果还是被动加成，让战斗更加生动真实)
"""
                                try:
                                    story_res = client.chat.completions.create(
                                        model=MODEL_NAME, messages=[{"role": "user", "content": prompt}]
                                    )
                                    story = story_res.choices[0].message.content.strip()
                                    title = f"[战胜]" if res=="战胜" else f"[同归于尽]" if res=="同归于尽" else f"[战败]"
                                    st.session_state.battle_log.insert(0, f"{title} <b>{monster['name']}</b><br><span style='color:#ccc;'>{story}</span>")
                                except:
                                    st.error("推演失败，只能继续前进。")
                            end_battle_cleanup(viewed_story=True)
                            
                    with c_cont:
                        if st.button("➡️ 继续前进", use_container_width=True):
                            end_battle_cleanup(viewed_story=False)


    # ------------------------------------------
    # Tab 2: 修为 (属性与道标)
    # ------------------------------------------
    with tab_cultivation:
        st.header("📜 本尊修为")
        st.markdown(f"**【{st.session_state.player_name}】** : 大境界 Lv {st.session_state.real_level}")
        st.progress(st.session_state.real_exp / 100.0, text=f"本尊灵力: {st.session_state.real_exp}/100")
        st.write("")
        
        stats = get_total_stats()
        categories = ['力量', '敏捷', '智力', '体质', '感知', '魅力']
        values = [stats['str'], stats['agi'], stats['int'], stats['con'], stats['wis'], stats['cha']]
        
        fig = go.Figure(data=go.Scatterpolar(
            r=values + [values[0]], theta=categories + [categories[0]], fill='toself', line_color='#ff4b4b', fillcolor='rgba(255, 75, 75, 0.3)'
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=False, range=[0, max(max(values) + 5, 20)]), bgcolor='rgba(0,0,0,0)'),
            showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=20, r=20, t=20, b=20), height=250, font=dict(color='#d4af37')
        )
        st.plotly_chart(fig, use_container_width=True)
        
        c1, c2, c3 = st.columns(3)
        def format_stat(base, total):
            bonus = total - base
            return f"{total} (+{bonus})" if bonus > 0 else (f"{total} ({bonus})" if bonus < 0 else str(total))
            
        c1.metric("力量 (力修)", format_stat(st.session_state.rpg_str, stats['str']))
        c2.metric("敏捷 (身法)", format_stat(st.session_state.rpg_agi, stats['agi']))
        c3.metric("智力 (悟性)", format_stat(st.session_state.rpg_int, stats['int']))
        
        c4, c5, c6 = st.columns(3)
        c4.metric("体质 (气血)", format_stat(st.session_state.rpg_con, stats['con']))
        c5.metric("感知 (神识)", format_stat(st.session_state.rpg_wis, stats['wis']))
        c6.metric("魅力 (机缘)", format_stat(st.session_state.rpg_cha, stats['cha']))
        
        st.markdown("---")
        st.header("🌟 现实道标")
        if st.session_state.real_skills:
            for skill_name, skill_data in st.session_state.real_skills.items():
                level = skill_data.get('level', 1)
                sub_level = skill_data.get('sub_level', 1)
                exp = skill_data.get('exp', 0)
                desc = skill_data.get('description', '')
                title = skill_data.get('title', '初窥门径')
                st.markdown(f"**{skill_name}** : {level}阶 ({title}) | {sub_level}重")
                st.caption(f"*{desc}*")
                st.progress(exp / 100.0, text=f"灵力积攒: {exp}%")
                st.write("")
        else:
            st.info("暂无专属技能，请在征战中记录你的现实成就。")
        st.markdown("---")
        st.header("✨ 羁绊共鸣 (Synergies)")
        
        # 统计当前激活的羁绊
        synergy_counts = get_synergy_counts()
                    
        if not synergy_counts:
            st.caption("当前未激活任何羁绊。装备带有同名羁绊标签的技能以激活套装特效。")
        else:
            for syn, count in synergy_counts.items():
                if count >= 6: level_str = "🔥 [6] 终极"
                elif count >= 4: level_str = "🌟 [4] 高级"
                elif count >= 2: level_str = "✨ [2] 初级"
                else: level_str = "⚪ [1] 未激活"
                
                st.markdown(f"**{syn}** : {count}/6 ({level_str})")
                
                # 简单的文本展示未来我们会接入的特效
                if syn == "剑修":
                    st.caption("[2] 攻击+15% | [4] 无视护甲 | [6] 额外剑气斩")
                elif syn == "魔道":
                    st.caption("[2] 附带吸血 | [4] 低血减伤 | [6] 满血复活")
                elif syn == "体修":
                    st.caption("[2] 气血+30% | [4] 开局护盾 | [6] 受到伤害反弹")
                elif syn == "法修":
                    st.caption("[2] 术法伤害+20% | [4] 无视魔抗 | [6] 双重施法")
                elif syn == "天道":
                    st.caption("[2] 全属性+5 | [4] 额外暴击闪避 | [6] 必定掉落神装")


    # ------------------------------------------
    # Tab 3: 行囊 (物品与悬赏)
    # ------------------------------------------
    with tab_inventory:
        def render_item_info(item):
            t_str = "主动技能" if item.get('type') == 'active' else "被动功法"
            syn_str = f" | 羁绊: {item.get('synergy', '无')}"
            eff_str = ""
            if item.get('type') == 'active':
                eff_map = {'nuke': '飞剑重击', 'vampire': '魔道血祭', 'shield': '屏障护盾', 'stun': '神识震慑', 'heal': '复苏之风'}
                eff_str = f" | 效果: {eff_map.get(item.get('skill_effect', 'nuke'), '未知')} (威力: {item.get('power', '未知')})"
            elif item.get('type') == 'passive':
                stat_map = {'str': '力量', 'agi': '敏捷', 'int': '智力', 'con': '体质', 'wis': '感知', 'cha': '魅力'}
                b_list = [f"{stat_map.get(k, k)}+{v}" if v>0 else f"{stat_map.get(k, k)}{v}" for k,v in item.get('stat_bonus', {}).items()]
                eff_str = f" | 加成: {', '.join(b_list)}"
            return f"<span style='color:#ffcc00;font-size:0.85em;'>[{t_str}{syn_str}{eff_str}]</span>"

        st.header("⚡ 功法构筑 (已装备)")
        col_act, col_pas = st.columns(2)
        
        with col_act:
            st.subheader("主动槽位 (3)")
            for idx in range(3):
                item = st.session_state.equipped_skills['active'][idx]
                if item is None:
                    st.markdown(f"**槽位 {idx+1}**：空")
                else:
                    st.markdown(f"**槽位 {idx+1}**：**{item['name']}** <br>{render_item_info(item)}", unsafe_allow_html=True)
                    if st.button("卸下", key=f"unequip_act_{idx}"):
                        st.session_state.inventory.append(item)
                        st.session_state.equipped_skills['active'][idx] = None
                        save_game(SAVE_KEY, ls_key=f"unequip_a_{idx}")
                        st.rerun()

        with col_pas:
            st.subheader("被动槽位 (3)")
            for idx in range(3):
                item = st.session_state.equipped_skills['passive'][idx]
                if item is None:
                    st.markdown(f"**槽位 {idx+1}**：空")
                else:
                    st.markdown(f"**槽位 {idx+1}**：**{item['name']}** <br>{render_item_info(item)}", unsafe_allow_html=True)
                    if st.button("卸下", key=f"unequip_pas_{idx}"):
                        st.session_state.inventory.append(item)
                        st.session_state.equipped_skills['passive'][idx] = None
                        save_game(SAVE_KEY, ls_key=f"unequip_p_{idx}")
                        st.rerun()

        st.markdown("---")
        st.header("🎒 须弥芥子 (未装备)")
        if not st.session_state.inventory:
            st.caption("行囊空空如也")
        else:
            for i, item in enumerate(st.session_state.inventory):
                st.markdown(f"**{item['name']}** <br>{render_item_info(item)}", unsafe_allow_html=True)
                st.caption(f"*{item['description']}*")
                
                t = item.get('type', 'passive')
                slots = st.session_state.equipped_skills[t]
                
                col_btn1, col_btn2, col_btn3, col_del = st.columns(4)
                with col_btn1:
                    if st.button("装备到槽位 1", key=f"equip_{i}_0"):
                        if slots[0] is not None: st.session_state.inventory.append(slots[0])
                        slots[0] = item
                        st.session_state.inventory.pop(i)
                        save_game(SAVE_KEY, ls_key=f"equip_{i}_0")
                        st.rerun()
                with col_btn2:
                    if st.button("装备到槽位 2", key=f"equip_{i}_1"):
                        if slots[1] is not None: st.session_state.inventory.append(slots[1])
                        slots[1] = item
                        st.session_state.inventory.pop(i)
                        save_game(SAVE_KEY, ls_key=f"equip_{i}_1")
                        st.rerun()
                with col_btn3:
                    if st.button("装备到槽位 3", key=f"equip_{i}_2"):
                        if slots[2] is not None: st.session_state.inventory.append(slots[2])
                        slots[2] = item
                        st.session_state.inventory.pop(i)
                        save_game(SAVE_KEY, ls_key=f"equip_{i}_2")
                        st.rerun()
                with col_del:
                    if st.button("丢弃", key=f"discard_{i}"):
                        st.session_state.inventory.pop(i)
                        save_game(SAVE_KEY, ls_key=f"discard_{i}")
                        st.rerun()
                st.write("")
        
        st.markdown("---")
        st.header("⚗️ 炼丹炉 (消耗品)")
        if not st.session_state.potions:
            st.caption("炉火已熄，暂无丹药")
        else:
            cols = st.columns(3)
            for i, potion in enumerate(st.session_state.potions):
                with cols[i % 3]:
                    if st.button(f"🍶 {potion['name']}", key=f"pot_{i}", help=potion.get('description', ''), use_container_width=True):
                        heal_amt = potion.get('heal', 30)
                        st.session_state.player_hp = min(st.session_state.player_max_hp, st.session_state.player_hp + heal_amt)
                        st.session_state.battle_log.insert(0, f"[服丹] 🍶 你服用了【{potion['name']}】，恢复了 {heal_amt} 点气血。")
                        st.session_state.potions.pop(i)
                        save_game(SAVE_KEY, ls_key=f"potion_use_{i}")
                        st.rerun()

        st.markdown("---")
        st.header("📜 天道榜文 (每日悬赏)")
        if not st.session_state.daily_quests:
            if st.button("🙏 求取今日悬赏", use_container_width=True):
                with st.spinner("天道正在推演你的因果..."):
                    try:
                        skills_info = ", ".join([f"{k}(Lv{v['level']})" for k,v in st.session_state.real_skills.items()]) if st.session_state.real_skills else "无基础"
                        quest_prompt = f"""根据用户的现实技能：[{skills_info}]，生成 2 个修仙风格现实任务。返回纯 JSON：{{"quests": [{{"task": "做30个俯卧撑", "desc": "天道见你体质虚浮...", "reward": "随机丹药名"}}]}}"""
                        q_res = client.chat.completions.create(model=MODEL_NAME, messages=[{"role": "user", "content": quest_prompt}], response_format={"type":"json_object"})
                        q_text = q_res.choices[0].message.content.strip()
                        if q_text.startswith("```json"): q_text = q_text[7:]
                        if q_text.startswith("```"): q_text = q_text[3:]
                        if q_text.endswith("```"): q_text = q_text[:-3]
                        st.session_state.daily_quests = json.loads(q_text).get("quests", [])
                        save_game(SAVE_KEY, ls_key="quest_get")
                        st.rerun()
                    except Exception as e:
                        st.error("天机遮蔽，求取失败")
        else:
            for i, quest in enumerate(st.session_state.daily_quests):
                with st.container():
                    st.markdown(f"**任务 {i+1}：{quest['task']}**")
                    st.caption(f"*{quest['desc']}* (奖励：{quest['reward']})")
                    if st.button(f"✅ 交付因果 (完成)", key=f"quest_{i}"):
                        st.session_state.potions.append({"name": quest['reward'], "heal": 50, "description": "天道赐福"})
                        st.session_state.daily_quests.pop(i)
                        st.session_state.battle_log.insert(0, f"[天道] 🌌 你完成了悬赏，获得【{quest['reward']}】！")
                        save_game(SAVE_KEY, ls_key=f"quest_done_{i}")
                        st.rerun()

    # ------------------------------------------
    # Tab 4: 岁月 (日志与历史)
    # ------------------------------------------
    with tab_history:
        # 在手机端或需要时，可以专门在这个 Tab 看日志
        st.header("📜 岁月日志 (完整记录)")
        log_html = "<div class='log-entry'>[系统] 命运的齿轮开始转动...</div>"
        for log in st.session_state.battle_log:
            log_html += f"<div class='log-entry'>{log}</div>"
            
        st.markdown(f"""
        <div class="battle-log" style="max-height: 400px; overflow-y: auto;">
            {log_html}
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.header("🗂️ 岁月史书 (过往成就)")
        for record in st.session_state.records:
            with st.container():
                st.markdown(f"**[{record['time']}]** 🌟 {record['action']}")
                st.markdown(f"<span style='color:#d4af37; font-size:0.9em;'>*获得：{record['result']}*</span>", unsafe_allow_html=True)
                st.divider()

    # ==========================================
    # 渲染右侧悬浮日志栏 (Right Sidebar Log) - 仅在大屏幕生效
    # ==========================================
    if st.session_state.game_stage == 'playing':
        log_html_right = "<h3>📜 岁月日志</h3>"
        log_html_right += "<div class='log-entry'>[系统] 命运的齿轮开始转动...</div>"
        for log in st.session_state.battle_log:
            log_html_right += f"<div class='log-entry'>{log}</div>"
            
        st.markdown(f"""
        <div class="right-sidebar-log">
            {log_html_right}
        </div>
        """, unsafe_allow_html=True)
