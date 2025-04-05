import json
import os
import random

# 创建示例数据目录
MOCK_DATA_DIR = "mock_data"
os.makedirs(MOCK_DATA_DIR, exist_ok=True)

def generate_mock_anime_list(count=20):
    """生成示例动漫列表数据"""
    anime_list = []
    
    titles = [
        "进击的巨人", "鬼灭之刃", "咒术回战", "一拳超人", "辉夜大小姐想让我告白", 
        "约定的梦幻岛", "DARLING in the FRANXX", "Re:从零开始的异世界生活", 
        "小林家的龙女仆", "总之就是非常可爱", "Charlotte", "Angel Beats!", 
        "路人女主的养成方法", "我的青春恋爱物语果然有问题", "辉夜姬想让人告白", 
        "紫罗兰永恒花园", "刀剑神域", "龙与虎", "工作细胞", "异度侵入"
    ]
    
    for i in range(1, count + 1):
        anime_id = str(40000 + i)
        title = titles[i - 1] if i <= len(titles) else f"示例动漫 {i}"
        
        anime = {
            "id": anime_id,
            "title": title,
            "cover_url": f"https://example.com/covers/{anime_id}.jpg",
            "update_info": f"更新至第{random.randint(1, 24)}集"
        }
        
        anime_list.append(anime)
    
    # 保存数据
    with open(os.path.join(MOCK_DATA_DIR, "anime_list.json"), "w", encoding="utf-8") as f:
        json.dump(anime_list, f, ensure_ascii=False, indent=2)
    
    print(f"已生成{count}条示例动漫列表数据")
    return anime_list

def generate_mock_anime_detail(anime_id, title=None):
    """生成示例动漫详情数据"""
    if not title:
        title = f"示例动漫 {anime_id}"
    
    # 生成剧集列表
    episodes_count = random.randint(12, 24)
    episodes = []
    
    for i in range(1, episodes_count + 1):
        episode_id = f"{anime_id}_{i}"
        episodes.append({
            "id": episode_id,
            "title": f"第{i}集",
            "href": f"/vod-play/{anime_id}/{episode_id}.html"
        })
    
    # 生成详情数据
    detail = {
        "id": anime_id,
        "db_id": random.randint(1, 1000),
        "title": title,
        "alias": f"{title} / {title} Season 1",
        "region": random.choice(["日本", "中国", "欧美"]),
        "year": str(random.randint(2015, 2023)),
        "description": "这是一个示例动漫的简介。内容丰富，剧情紧凑，人物形象鲜明，画面精美，值得一看。" * 3,
        "cover_url": f"https://example.com/covers/{anime_id}.jpg",
        "episodes": episodes,
        "total_episodes": episodes_count
    }
    
    # 保存数据
    with open(os.path.join(MOCK_DATA_DIR, f"anime_detail_{anime_id}.json"), "w", encoding="utf-8") as f:
        json.dump(detail, f, ensure_ascii=False, indent=2)
    
    print(f"已生成动漫 {title}(ID:{anime_id}) 的详情数据，共{episodes_count}集")
    return detail

def generate_mock_video_url(anime_id, episode_id):
    """生成示例视频地址数据"""
    video_data = {
        "anime_id": anime_id,
        "episode_id": episode_id,
        "video_url": f"https://example.com/player/{anime_id}/{episode_id}.mp4"
    }
    
    # 保存数据
    with open(os.path.join(MOCK_DATA_DIR, f"video_url_{anime_id}_{episode_id}.json"), "w", encoding="utf-8") as f:
        json.dump(video_data, f, ensure_ascii=False, indent=2)
    
    print(f"已生成视频地址数据：动漫ID {anime_id}，剧集ID {episode_id}")
    return video_data["video_url"]

def generate_search_results(count=10):
    """生成搜索结果数据"""
    return generate_mock_anime_list(count)

def generate_all_mock_data():
    """生成所有示例数据"""
    # 生成动漫列表
    anime_list = generate_mock_anime_list(20)
    
    # 为每个动漫生成详情
    for anime in anime_list:
        detail = generate_mock_anime_detail(anime["id"], anime["title"])
        
        # 为第一集生成视频地址
        if detail["episodes"] and len(detail["episodes"]) > 0:
            first_episode = detail["episodes"][0]
            generate_mock_video_url(anime["id"], first_episode["id"])
    
    # 生成搜索结果数据
    search_results = generate_search_results()
    with open(os.path.join(MOCK_DATA_DIR, "search_results.json"), "w", encoding="utf-8") as f:
        json.dump(search_results, f, ensure_ascii=False, indent=2)
    print("已生成搜索结果数据")
    
    print("所有示例数据生成完成")

if __name__ == "__main__":
    generate_all_mock_data() 