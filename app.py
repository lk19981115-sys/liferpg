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

def save_game(key=SAVE_KEY):
    keys_to_save = [
        "game_stage", "player_name", "real_skills", "real_exp", "real_level",
        "rpg_str", "rpg_agi", "rpg_int", "rpg_con", "rpg_wis", "rpg_cha",
        "player_hp", "player_max_hp", "monster", "battle_log", "records",
        "inventory", "pending_loot", "death_time", "potions", "daily_quests", "is_boss"
    ]
    data_to_save = {k: st.session_state[k] for k in keys_to_save if k in st.session_state}
    # 将数据存入浏览器 localStorage
    localS.setItem(key, json.dumps(data_to_save, ensure_ascii=False))

def delete_game(key):
    localS.deleteAll() # localS 插件 deleteItem 有时不稳定，这里需要小心处理，或者直接覆写为空
    # 实际上更安全的方式是覆写为空
    localS.setItem(key, "")

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
                            "inventory", "pending_loot", "death_time", "potions", "daily_quests", "is_boss"
                        ]
                        for k in keys_to_clear:
                            if k in st.session_state:
                                del st.session_state[k]
                        # 载入新数据
                        for k, v in slot_data.items():
                            st.session_state[k] = v
                        # 同时覆盖自动存档
                        save_game(SAVE_KEY)
                        st.success(f"已读取存档 {slot}！")
                        st.rerun()
                with col_b:
                    if st.button("覆盖", key=f"save_over_{slot}", help="覆盖此存档"):
                        save_game(slot_key)
                        st.success(f"已覆盖存档 {slot}！")
                        st.rerun()
                with col_c:
                    if st.button("删除", key=f"del_{slot}", help="删除此存档"):
                        delete_game(slot_key)
                        st.warning(f"已删除存档 {slot}。")
                        st.rerun()
            else:
                st.markdown(f"**存档 {slot}** - 空")
                # 如果没有存档，显示保存或从新开始
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("保存当前", key=f"save_new_{slot}"):
                        save_game(slot_key)
                        st.success(f"游戏已保存至槽位 {slot}！")
                        st.rerun()
                with col_b:
                    if st.button("从新开始", key=f"new_game_{slot}"):
                        # 清空内存数据，直接回到创角阶段
                        keys_to_clear = [
                            "game_stage", "player_name", "real_skills", "real_exp", "real_level",
                            "rpg_str", "rpg_agi", "rpg_int", "rpg_con", "rpg_wis", "rpg_cha",
                            "player_hp", "player_max_hp", "monster", "battle_log", "records",
                            "inventory", "pending_loot", "death_time", "potions", "daily_quests", "is_boss"
                        ]
                        for k in keys_to_clear:
                            if k in st.session_state:
                                del st.session_state[k]
                        st.session_state.game_stage = 'character_creation'
                        # 同时将这个初始状态保存到对应的槽位和自动存档中
                        save_game(slot_key)
                        save_game(SAVE_KEY)
                        st.rerun()
            
            st.markdown("---")

    st.header("🛠️ 开发者通道")
    dev_pwd = st.text_input("输入密钥", type="password")
    if dev_pwd == "981115":
        st.success("开发者模式已解锁")
        st.session_state.dev_op_loot = st.toggle("开启：大道金榜 (无视等级掉落神装)", value=st.session_state.dev_op_loot)
        if st.button("✨ 逆转时空 (复活并满血)"):
            st.session_state.player_hp = st.session_state.player_max_hp
            st.session_state.death_time = None
            save_game()
            st.rerun()

# ==========================================
# 2. 路由逻辑：创角页面 vs 主游戏页面
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
        **LifeRPG** 是一款将你现实中的努力转化为游戏属性的自我提升引擎。在这里，现实即是副本，你就是那个主角！
        
        1. **现实道标 (左侧)**：代表你现实中正在学习或锻炼的技能。你现实中的每一次精进，都会在这里转化为具体的等级与经验值。
        2. **命运深渊 (右侧)**：你将面临各种虚拟怪物（如“拖延症缝合怪”、“懒惰心魔”）。你的现实属性越高，在战斗中造成的伤害就越大。
        3. **命运纺锤 (底部)**：每天在此记录你完成的现实成就。AI 将根据你的成就自动为你分配经验，并生成一场波澜壮阔的 RPG 战斗！
        4. **岁月史书 (底部)**：查看你过往的日程与努力记录，见证你跨越凡尘的每一步脚印。
        """)

    st.markdown("---")

    # ==========================================
    # 2. 页面主体布局：左右对等两列
    # ==========================================
    col1, col2 = st.columns(2)

    # ------------------------------------------
    # 左侧面板：System I - 现实道标
    # ------------------------------------------
    with col1:
        st.header("📜 现实道标 (Reality Cultivation)")
        st.caption("在这里，你现实中的每一次精进，都在转化为修真的底蕴...")
        st.write("") # 留白
        
        # 显示真实的等级和经验 (整体大境界)
        st.markdown(f"**【{st.session_state.player_name} 境界】** : Lv {st.session_state.real_level}")
        st.progress(st.session_state.real_exp / 100.0, text=f"本尊灵力: {st.session_state.real_exp}/100")
        st.write("---")
        
        # 动态渲染用户的专属技能树
        if st.session_state.real_skills:
            for skill_name, skill_data in st.session_state.real_skills.items():
                level = skill_data.get('level', 1)
                sub_level = skill_data.get('sub_level', 1)
                exp = skill_data.get('exp', 0)
                desc = skill_data.get('description', '')
                title = skill_data.get('title', '初窥门径')
                
                st.markdown(f"**{skill_name}** : 大境界 {level}阶 ({title}) | 小境界 {sub_level}重")
                st.caption(f"*{desc}*")
                st.progress(exp / 100.0, text=f"灵力积攒: {exp}%")
                st.write("")
        else:
            st.info("暂无专属技能，请在命运纺锤中记录你的现实成就。")

        st.markdown("---")
        st.header("📜 天道榜文 (每日悬赏)")
        st.caption("天道察觉你的不足，特降下试炼。完成可获丰厚天道赐福。")
        
        if not st.session_state.daily_quests:
            if st.button("🙏 求取今日悬赏"):
                with st.spinner("天道正在推演你的因果..."):
                    try:
                        skills_info = ", ".join([f"{k}(Lv{v['level']})" for k,v in st.session_state.real_skills.items()]) if st.session_state.real_skills else "无基础"
                        quest_prompt = f"""根据用户的当前现实技能：[{skills_info}]，找出他的弱点或结合现实生活，生成 2 个修仙风格的现实每日任务。
要求返回纯 JSON 格式，不要 Markdown 标记：
{{
  "quests": [
    {{"task": "现实任务内容（如：做30个俯卧撑）", "desc": "修仙风格的描述（如：天道见你体质虚浮...）", "reward": "随机一种丹药的名称"}}
  ]
}}"""
                        q_res = client.chat.completions.create(model=MODEL_NAME, messages=[{"role": "user", "content": quest_prompt}], response_format={"type":"json_object"})
                        q_text = q_res.choices[0].message.content.strip()
                        if q_text.startswith("```json"): q_text = q_text[7:]
                        if q_text.startswith("```"): q_text = q_text[3:]
                        if q_text.endswith("```"): q_text = q_text[:-3]
                        st.session_state.daily_quests = json.loads(q_text).get("quests", [])
                        save_game()
                        st.rerun()
                    except Exception as e:
                        st.error(f"天机遮蔽，求取失败: {str(e)}")
        else:
            for i, quest in enumerate(st.session_state.daily_quests):
                with st.container():
                    st.markdown(f"**任务 {i+1}：{quest['task']}**")
                    st.caption(f"*{quest['desc']}* (奖励：{quest['reward']})")
                    if st.button(f"✅ 交付因果 (完成任务 {i+1})", key=f"quest_{i}"):
                        st.session_state.potions.append({"name": quest['reward'], "heal": 50, "description": "天道赐福，服之可恢复大量气血"})
                        st.session_state.daily_quests.pop(i)
                        st.session_state.battle_log.insert(0, f"[天道] 🌌 你完成了天道悬赏，获得了一枚【{quest['reward']}】！")
                        save_game()
                        st.rerun()

    # ------------------------------------------
    # 右侧面板：System II - 命运深渊
    # ------------------------------------------
    # ------------------------------------------
    # 右侧面板：System II - 命运深渊
    # ------------------------------------------
    with col2:
        st.header("⚔️ 命运深渊 (RPG Combat)")
        st.caption("直面你的心魔与挑战，让属性化作破局的利刃...")
        st.write("")
        
        # 玩家气血区
        st.markdown(f"**{st.session_state.player_name} 的气血 (HP)**: {st.session_state.player_hp} / {st.session_state.player_max_hp}")
        st.progress(max(0.0, st.session_state.player_hp / st.session_state.player_max_hp))
        st.write("")
        
        # 角色属性区 (六维展示)
        categories = ['力量', '敏捷', '智力', '体质', '感知', '魅力']
        values = [st.session_state.rpg_str, st.session_state.rpg_agi, st.session_state.rpg_int, 
                  st.session_state.rpg_con, st.session_state.rpg_wis, st.session_state.rpg_cha]
        
        fig = go.Figure(data=go.Scatterpolar(
            r=values + [values[0]],
            theta=categories + [categories[0]],
            fill='toself',
            line_color='#ff4b4b',
            fillcolor='rgba(255, 75, 75, 0.3)'
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=False, range=[0, max(max(values) + 5, 20)]),
                bgcolor='rgba(0,0,0,0)'
            ),
            showlegend=False,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=20, t=20, b=20),
            height=250,
            font=dict(color='#d4af37')
        )
        st.plotly_chart(fig, use_container_width=True)
        
        m1, m2, m3 = st.columns(3)
        m1.metric("力量 (力修)", str(st.session_state.rpg_str))
        m2.metric("敏捷 (身法)", str(st.session_state.rpg_agi))
        m3.metric("智力 (悟性)", str(st.session_state.rpg_int))
        
        m4, m5, m6 = st.columns(3)
        m4.metric("体质 (气血)", str(st.session_state.rpg_con))
        m5.metric("感知 (神识)", str(st.session_state.rpg_wis))
        m6.metric("魅力 (机缘)", str(st.session_state.rpg_cha))
        
        st.markdown("---")
        
        # 道具栏展示
        st.markdown("##### 🎒 须弥芥子 (道具栏 - 上限3个)")
        if not st.session_state.inventory:
            st.caption("空空如也")
        else:
            for i, item in enumerate(st.session_state.inventory):
                st.markdown(f"**{i+1}. {item['name']}** - *{item['description']}*")
        
        st.markdown("---")
        
        # 炼丹炉系统
        st.markdown("##### ⚗️ 炼丹炉 (消耗品)")
        if not st.session_state.potions:
            st.caption("炉火已熄，暂无丹药")
        else:
            num_cols = min(len(st.session_state.potions), 4)
            cols = st.columns(num_cols)
            for i, potion in enumerate(st.session_state.potions):
                with cols[i % num_cols]:
                    if st.button(f"🍶 {potion['name']}", key=f"pot_{i}", help=potion.get('description', '')):
                        heal_amt = potion.get('heal', 30)
                        st.session_state.player_hp = min(st.session_state.player_max_hp, st.session_state.player_hp + heal_amt)
                        st.session_state.battle_log.insert(0, f"[服丹] 🍶 你服用了【{potion['name']}】，恢复了 {heal_amt} 点气血。")
                        st.session_state.potions.pop(i)
                        save_game()
                        st.rerun()
        
        st.markdown("---")
        
        # 当前遭遇战 (使用动态怪物数据)
        monster = st.session_state.monster
        if st.session_state.get('is_boss', False):
            st.markdown(f"<h3 class='encounter-title'>⚡ 【天劫降临】 [Lv {monster['level']}] {monster['name']}</h3>", unsafe_allow_html=True)
        else:
            st.markdown(f"<h4 class='encounter-title'>🔥 当前遭遇：[Lv {monster['level']}] {monster['name']}</h4>", unsafe_allow_html=True)
        st.caption(f"*{monster['description']}* (战力评估: {monster['defense'] * 10})")
        
        hp_ratio = max(0.0, monster['hp'] / monster['max_hp'])
        st.progress(hp_ratio, text=f"妖兽气血: {monster['hp']}/{monster['max_hp']}")
        st.write("")
        
        # 新增：手动战斗与掉落系统
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
                save_game()
        
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
                                save_game()
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
                            save_game()
                            st.rerun()
                    with col_b:
                        if st.button("取消选择"):
                            del st.session_state.selected_loot
                            st.rerun()
                
                st.markdown("---")
                if st.button("🗑️ 放弃所有战利品"):
                    st.session_state.pending_loot = []
                    if 'selected_loot' in st.session_state:
                        del st.session_state.selected_loot
                    save_game()
                    st.rerun()

        elif st.session_state.player_hp <= 1 and can_fight:
            st.error("⚠️ 你的气血已见底，强行出战必死无疑。请先通过【命运纺锤】进行现实修炼，恢复气血！")
        elif can_fight:
            if st.button("⚔️ 拔剑！生死斗法", use_container_width=True):
                with st.spinner("⚔️ 刀光剑影，灵气激荡，推演中..."):
                    try:
                        # 动态获取用户当前的技能列表和状态
                        skills_str = ", ".join(st.session_state.real_skills.keys()) if st.session_state.real_skills else "通用经验"
                        inv_str = ", ".join([f"{item['name']}({item['description']})" for item in st.session_state.inventory]) if st.session_state.inventory else "无"
                        
                        is_boss = st.session_state.get('is_boss', False)
                        boss_rule = "注意：这是【天劫/心魔】Boss战！玩家绝对无法逃跑（如果玩家实力不济，即使想逃跑也必须被天劫重创，返回 lose），Boss极其强大，战斗过程要描写得毁天灭地！" if is_boss else ""

                        combat_prompt = f"""你是一个《凡人修仙传》风格的文字RPG游戏引擎兼修仙小说作家。 
现在发生了一场生死斗法！请你进行一次完整的战斗推演，直接决出胜负。

【对战双方状态】
玩家尊号（主角名字）：{st.session_state.player_name}
玩家携带法宝/道具：{inv_str}
玩家六维属性：力量{st.session_state.rpg_str}，敏捷{st.session_state.rpg_agi}，智力{st.session_state.rpg_int}，体质{st.session_state.rpg_con}，感知{st.session_state.rpg_wis}，魅力{st.session_state.rpg_cha}
玩家气血：{st.session_state.player_hp}/{st.session_state.player_max_hp}
妖兽信息：[{st.session_state.monster['level']}级] {st.session_state.monster['name']}
妖兽战力/护甲：{st.session_state.monster['defense']}
妖兽气血：{st.session_state.monster['hp']}/{st.session_state.monster['max_hp']}

【推演规则】
1. 综合对比玩家的六维属性与妖兽的战力。如果玩家主属性(力/敏/智)远大于妖兽战力，玩家可以轻松斩杀；如果相近，则是苦战惨胜；如果远低于，玩家将不敌败退或重伤逃遁。
{boss_rule}
2. 必须生成一段 200-400 字的详细战斗小说片段（包含功法碰撞、法宝交锋、惊险躲避等修仙小说常见桥段）。**请在小说中直接使用玩家的尊号“{st.session_state.player_name}”作为主角名字进行描写，不要使用“韩立”等其他无关的默认名字！并且必须在战斗中生动地描写玩家如何使用上述携带的【法宝/道具】克敌制胜！**
3. 战斗必须在这段文字的结尾分出明确胜负！

你必须，且只能返回纯 JSON 格式的数据，不要包含任何 Markdown 标记！ 

JSON 格式必须包含以下字段： 
{{ 
"result": "win" (玩家胜利，妖兽死亡), "lose" (玩家重伤败退，妖兽存活), "escape" (敏捷高，玩家轻伤逃跑，妖兽存活),
"combat_story": "修仙战斗小说片段...", 
"player_hp_left": 战斗后玩家剩余气血(如果是 win 且碾压，可不扣血；如果是 lose，必须扣到 1 滴血代表重伤；escape 扣部分血量),
"monster_hp_left": 战斗后妖兽剩余气血(如果是 win 必须为0；如果是 lose 或 escape，根据战斗情况扣除部分血量)
}}"""

                        response = client.chat.completions.create(
                            model=MODEL_NAME,
                            messages=[
                                {"role": "system", "content": combat_prompt},
                                {"role": "user", "content": "我祭出法宝，与妖兽战作一团！"}
                            ],
                            response_format={ "type": "json_object" }
                        )
                        
                        result_text = response.choices[0].message.content.strip()
                        if result_text.startswith("```json"): result_text = result_text[7:]
                        if result_text.startswith("```"): result_text = result_text[3:]
                        if result_text.endswith("```"): result_text = result_text[:-3]
                            
                        combat_data = json.loads(result_text)
                        
                        result = combat_data.get("result", "lose")
                        combat_story = combat_data.get("combat_story", "一场激烈的战斗发生了...")
                        
                        # 更新血量
                        st.session_state.player_hp = max(1, min(st.session_state.player_max_hp, combat_data.get("player_hp_left", 1)))
                        st.session_state.monster['hp'] = max(0, combat_data.get("monster_hp_left", st.session_state.monster['hp']))
                        
                        st.session_state.battle_log.insert(0, f"[斗法记录]<br><span style='color:#ccc;'>{combat_story}</span>")
                        
                        # 战斗结果处理
                        if result == "win" or st.session_state.monster['hp'] <= 0:
                            st.session_state.monster['hp'] = 0
                            if st.session_state.get('is_boss', False):
                                st.session_state.battle_log.insert(0, f"[渡劫成功] ⚡ 苍穹震怒，金光洒下！你成功斩杀了天劫心魔【{st.session_state.monster['name']}】，大道可期！")
                            else:
                                st.session_state.battle_log.insert(0, f"[大捷] 🎊 你成功斩杀了【{st.session_state.monster['name']}】！")
                            
                            new_level = st.session_state.monster['level'] + 1
                            is_next_boss = (new_level % 10 == 0)
                            st.session_state.is_boss = is_next_boss
                            
                            monster_type = "【天劫心魔】级别，极其恐怖的守关Boss" if is_next_boss else "普通妖兽"
                            
                            # 调用 AI 生成《凡人修仙传》风格的怪物
                            monster_prompt = f"""请生成一只《凡人修仙传》风格的修仙界妖兽。
这只妖兽的等级是 {new_level} 级。类型是：{monster_type}。请给它起一个符合修仙背景的霸气名字（如：六翼霜蚣、噬金虫、墨蛟、血玉蜘蛛等），并给出一句简短的背景描述。
返回纯 JSON 格式：
{{
"name": "妖兽名字",
"description": "妖兽背景描述"
}}"""
                            try:
                                monster_response = client.chat.completions.create(
                                    model=MODEL_NAME,
                                    messages=[{"role": "user", "content": monster_prompt}],
                                    response_format={ "type": "json_object" }
                                )
                                m_text = monster_response.choices[0].message.content.strip()
                                if m_text.startswith("```json"): m_text = m_text[7:]
                                if m_text.startswith("```"): m_text = m_text[3:]
                                if m_text.endswith("```"): m_text = m_text[:-3]
                                m_data = json.loads(m_text)
                                new_name = m_data.get("name", f"不知名妖兽(Lv{new_level})")
                                new_desc = m_data.get("description", "深渊中孕育的更强魔物。")
                            except:
                                import random
                                boss_names = ["六翼霜蚣", "噬金虫", "墨蛟", "血玉蜘蛛", "啼魂兽"]
                                prefix = "【天劫】" if is_next_boss else random.choice(['百年', '千年', '万年'])
                                new_name = f"[{prefix}] {random.choice(boss_names)}"
                                new_desc = "深渊中孕育的更强妖兽，散发着令人窒息的妖气。"
                            
                            new_max_hp = (100 + (new_level * 50)) * (3 if is_next_boss else 1)
                            new_defense = (5 + (new_level * 3)) * (2 if is_next_boss else 1)
                            
                            st.session_state.monster = {
                                "name": new_name,
                                "level": new_level,
                                "hp": new_max_hp,
                                "max_hp": new_max_hp,
                                "defense": new_defense,
                                "description": new_desc
                            }
                            if is_next_boss:
                                st.session_state.battle_log.insert(0, f"[天劫酝酿] ⛈️ 苍穹变色！【天劫心魔】Lv {new_level} 的 {new_name} 已锁定你！(战力: {new_defense * 10})")
                            else:
                                st.session_state.battle_log.insert(0, f"[异变] ⚠️ 妖气冲天！Lv {new_level} 的 {new_name} 出现了！(战力: {new_defense * 10})")
                            
                            # 生成战利品掉落
                            loot_level = st.session_state.real_level
                            if st.session_state.dev_op_loot or st.session_state.get('is_boss', False):
                                loot_prompt_level = "仙界至高无上（直接掉落诸天万界最顶级的先天灵宝，威力毁天灭地）"
                            else:
                                if loot_level <= 3:
                                    loot_prompt_level = "凡人兵器或残破法器（如铁剑、破木盾、凡人书籍等）"
                                elif loot_level <= 6:
                                    loot_prompt_level = "筑基期/结丹期法器"
                                else:
                                    loot_prompt_level = "夺天地造化的灵宝/古宝"

                            loot_prompt = f"""请生成 3 个符合《凡人修仙传》风格的战利品道具，供玩家选择。
当前掉落品阶为：{loot_prompt_level}。
返回纯 JSON 格式：
{{
"loot": [
    {{"name": "道具1名称", "description": "简短的功效和外观描述"}},
    {{"name": "道具2名称", "description": "简短的功效和外观描述"}},
    {{"name": "道具3名称", "description": "简短的功效和外观描述"}}
]
}}"""
                            try:
                                loot_res = client.chat.completions.create(
                                    model=MODEL_NAME,
                                    messages=[{"role": "user", "content": loot_prompt}],
                                    response_format={ "type": "json_object" }
                                )
                                l_text = loot_res.choices[0].message.content.strip()
                                if l_text.startswith("```json"): l_text = l_text[7:]
                                if l_text.startswith("```"): l_text = l_text[3:]
                                if l_text.endswith("```"): l_text = l_text[:-3]
                                l_data = json.loads(l_text)
                                st.session_state.pending_loot = l_data.get("loot", [])
                            except:
                                st.session_state.pending_loot = [{"name": "神秘残片", "description": "散发着微弱灵光的残片"}]
                        
                        elif result == "lose":
                            st.session_state.battle_log.insert(0, f"[重伤] 🩸 你不敌【{st.session_state.monster['name']}】，身受重伤，气血只剩 1 滴！肉身需要 24 小时重塑。")
                            st.session_state.death_time = datetime.datetime.now().isoformat()
                            if st.session_state.get('is_boss', False):
                                drop_exp = 50
                                st.session_state.real_exp = max(0, st.session_state.real_exp - drop_exp)
                                st.session_state.battle_log.insert(0, f"[天道反噬] ⚡ 渡劫失败！本尊灵力大损，修为倒退 {drop_exp} 点！")
                        else:
                            st.session_state.battle_log.insert(0, f"[败退] 💨 你自知不敌，施展遁术惊险逃脱。")
                            
                        save_game()
                        st.rerun()
                    except Exception as e:
                        st.error(f"战斗推演失败: {str(e)}")

        st.write("")
        
        # 战斗日志 (Battle Log)
        st.markdown("##### 📜 战斗日志")
        
        # 渲染战斗日志内容
        log_content = "[系统] 命运的齿轮开始转动...<br>"
        for log in st.session_state.battle_log:
            log_content += f"{log}<br>"
            
        st.markdown(f"""
        <div class="battle-log">
            {log_content}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ==========================================
    # 3. 底部交互区：命运纺锤 (Action Input)
    # ==========================================
    st.header("⏳ 命运纺锤 (Action Input)")
    st.caption("向命运纺锤献上你今日的现实成就，将其化为破局的力量吧！")

    # 使用 form 将输入框和按钮包裹起来，方便一键提交处理
    with st.form("action_form"):
        action_input = st.text_input(
            "你的现实成就", 
            placeholder="记录你今天的现实成就（例如：今天读了 20 页英文研报，写了 3000 字小说）...",
            label_visibility="collapsed" # 隐藏输入框标题，让界面更简洁
        )
        
        # 醒目的提交按钮
        submitted = st.form_submit_button("✨ 注入经验")
        
        # ==========================================
        # 4. 回调逻辑处理区 (预留 LLM API 接口)
        # ==========================================
        if submitted:
            if action_input.strip() == "":
                st.warning("⚠️ 纺锤空空如也，请先记录你的现实成就！")
            else:
                with st.spinner("✨ 经验已注入，AI 正在演算战局..."):
                    try:
                        # ----------------------------------------------------
                        # 调用 Gemini 大模型 (使用官方 SDK)
                        # ----------------------------------------------------
                        # 动态获取用户当前的技能列表，告诉 AI 可以加哪些技能的经验
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
                        
                        # 解析返回的 JSON 数据
                        result_text = response.choices[0].message.content.strip()
                        if result_text.startswith("```json"):
                            result_text = result_text[7:]
                        if result_text.startswith("```"):
                            result_text = result_text[3:]
                        if result_text.endswith("```"):
                            result_text = result_text[:-3]
                            
                        result_data = json.loads(result_text)
                        
                        # ----------------------------------------------------
                        # 解析 JSON 并处理业务逻辑
                        # ----------------------------------------------------
                        system_action = result_data.get("system_action", "add_exp")
                        feedback_message = result_data.get("feedback_message", "")
                        
                        if system_action == "modify_skills":
                            # 处理系统管理指令 (拆分、重命名等)
                            instructions = result_data.get("modify_instructions", {})
                            action = instructions.get("action", "none")
                            target_skill = result_data.get("target_skill", "")
                            new_skills = instructions.get("new_skills", [])
                            
                            if action == "split" or action == "rename":
                                if target_skill in st.session_state.real_skills:
                                    old_skill_data = st.session_state.real_skills.pop(target_skill)
                                    # 将旧技能的经验平分或继承给新技能
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
                            
                            # 更新日程表记录为系统指令
                            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                            st.session_state.records.insert(0, {
                                "time": now,
                                "action": f"【指令】{action_input}",
                                "result": "系统道标已重塑"
                            })
                            
                        else:
                            # ----------------------------------------------------
                            # 处理正常的修炼逻辑 (增加经验与属性)
                            # ----------------------------------------------------
                            exp_gained = result_data.get("exp_gained", 10)
                            target_skill = result_data.get("target_skill", "通用经验")
                            is_new_skill = result_data.get("is_new_skill", False)
                            
                            # 1. 动态新增技能逻辑
                            if is_new_skill and target_skill not in st.session_state.real_skills:
                                st.session_state.real_skills[target_skill] = {
                                    "level": 1,
                                    "sub_level": 1,
                                    "exp": 0,
                                    "description": result_data.get("new_skill_desc", "一条崭新的修真大道。"),
                                    "title": "初窥门径"
                                }
                                st.session_state.battle_log.insert(0, f"[顿悟] 🎇 你的行为引动了天地法则，开辟了新的道标：【{target_skill}】！")
    
                            # 2. 更新专属技能经验
                            if target_skill in st.session_state.real_skills:
                                skill = st.session_state.real_skills[target_skill]
                                skill['exp'] += exp_gained
                                # 专属技能升级逻辑 (每100经验升1小阶，满10阶升1大境界)
                                if skill['exp'] >= 100:
                                    levels_up = skill['exp'] // 100
                                    skill['exp'] = skill['exp'] % 100
                                    skill['sub_level'] += levels_up
                                    
                                    if skill['sub_level'] > 10:
                                        major_levels_up = skill['sub_level'] // 10
                                        skill['sub_level'] = skill['sub_level'] % 10
                                        if skill['sub_level'] == 0: # 避免出现 0 重的情况
                                            skill['sub_level'] = 10
                                            major_levels_up -= 1
                                        skill['level'] += major_levels_up
                                        
                                        # 升大境界时，动态请求一个新称号
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
    
                            # 3. 同时增加本尊总经验 (用于提升本尊大境界)
                            master_exp_gained = max(1, exp_gained // 2)
                            st.session_state.real_exp += master_exp_gained
                            if st.session_state.real_exp >= 100:
                                st.session_state.real_level += 1
                                st.session_state.real_exp -= 100
                                st.session_state.battle_log.insert(0, f"[飞升] 👑 苍穹震动！【{st.session_state.player_name}】的境界提升到了 Lv {st.session_state.real_level}！")
                                
                            # ----------------------------------------------------
                            # 更新状态 (现实经验 -> 战斗属性的转化与气血恢复)
                            # ----------------------------------------------------
                            stat_up = result_data.get("stat_up", "")
                            if "力量" in stat_up: st.session_state.rpg_str += int(''.join(filter(str.isdigit, stat_up)) or 1)
                            elif "敏捷" in stat_up: st.session_state.rpg_agi += int(''.join(filter(str.isdigit, stat_up)) or 1)
                            elif "智力" in stat_up: st.session_state.rpg_int += int(''.join(filter(str.isdigit, stat_up)) or 1)
                            elif "体质" in stat_up: 
                                st.session_state.rpg_con += int(''.join(filter(str.isdigit, stat_up)) or 1)
                                st.session_state.player_max_hp = st.session_state.rpg_con * 10
                            elif "感知" in stat_up: st.session_state.rpg_wis += int(''.join(filter(str.isdigit, stat_up)) or 1)
                            elif "魅力" in stat_up: st.session_state.rpg_cha += int(''.join(filter(str.isdigit, stat_up)) or 1)
                                
                            # 每次修炼都能恢复一定气血 (20% - 50%)
                            heal_amount = int(st.session_state.player_max_hp * (0.2 + (exp_gained / 200.0)))
                            st.session_state.player_hp = min(st.session_state.player_max_hp, st.session_state.player_hp + heal_amount)
                                
                            st.session_state.battle_log.insert(0, f"[修炼] {feedback_message} (气血恢复 {heal_amount} 点)")
                            
                            # 丹药掉落处理
                            potion_drop = result_data.get("potion_drop")
                            if potion_drop and isinstance(potion_drop, dict) and "name" in potion_drop:
                                st.session_state.potions.append(potion_drop)
                                st.session_state.battle_log.insert(0, f"[炼丹] ⚗️ 天道感应到你的日常微小努力，赐下了一枚【{potion_drop.get('name', '神秘丹药')}】！")
                                
                            # ----------------------------------------------------
                            # 更新日程表记录
                            # ----------------------------------------------------
                            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                            record_result = f"【{target_skill}】经验 +{exp_gained}, {stat_up}"
                            st.session_state.records.insert(0, {
                                "time": now,
                                "action": action_input,
                                "result": record_result
                            })
                        
                        # 刷新页面以更新 UI
                        save_game()
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"API 调用或解析失败: {str(e)}")
                        st.info("原返回内容: " + result_text if 'result_text' in locals() else "无")

    st.markdown("---")

    # ==========================================
    # 5. 日程表/历史记录区：岁月史书 (Records)
    # ==========================================
    st.header("🗂️ 岁月史书 (Chronicles)")
    st.caption("这里铭刻着你跨越凡尘的每一步脚印，记录着你过往的现实成就。")

    # 用循环渲染记录卡片，展示历史记录
    for record in st.session_state.records:
        with st.container():
            st.markdown(f"**[{record['time']}]** 🌟 {record['action']}")
            st.markdown(f"<span style='color:#d4af37; font-size:0.9em;'>*获得：{record['result']}*</span>", unsafe_allow_html=True)
            st.divider() # 每条记录之间加个分割线
