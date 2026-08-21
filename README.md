**Daily digest page: https://Wadesha.github.io/reddit-daily/**

# Reddit 姣忔棩閫熻锛圖aily Reddit Digest锛?
姣忓ぉ鑷姩鎶撳彇 **107 涓?Reddit 鐗堝潡**鐨勭儹闂ㄥ笘瀛愶紙**閲嶇偣鐗堝潡闄勫甫楂樿禐璇勮**锛夛紝鐢熸垚绱у噾涓嫳鍙岃閫熻椤碉紝鍙戝竷鍒?GitHub Pages銆?鏁版嵁鏉ヨ嚜 Reddit 瀹樻柟鍏紑鎺ュ彛锛屼釜浜洪潪鍟嗕笟鐢ㄩ€旓紝浣庨鐜囷紙姣忓ぉ涓€娆★級锛岄摼鎺ュ潎鍥炲師甯栥€?
## 鐗规€?
- **涓嫳鍙岃**锛氳嫳鏂囨爣棰?+ 涓枃鐗堝潡鍚嶏紱閰嶇疆 `LLM_API_KEY` 鍚庡彲鑷姩缈昏瘧鏍囬
- **璺熷笘鏀寔**锛氶噸鐐圭増鍧楋紙绾?29 涓級姣忓ぉ鎶撴瘡甯?top 3-5 鏉￠珮璧炶瘎璁猴紝鏄剧ず鍦ㄥ笘瀛愪笅鏂?- **鍔ㄦ€佽皟鑺?*锛氭瘡涓増鍧楀彲鐙珛閰嶇疆鎶撳彇寮哄害锛屾敼涓€琛?JSON 娆℃棩鐢熸晥锛堣涓嬶級
- **鑷姩鎺㈢储**锛氭瘡澶╀粠 Reddit 鐑棬姒滃崟鍙戠幇鏂扮増鍧楋紝灞曠ず鍦ㄩ〉闈㈠簳閮?鎺㈢储鎺ㄨ崘"鍖?- **绾潤鎬?*锛欸itHub Pages 鍏嶈垂鎵樼锛屾墦寮€缃戝潃鍗崇湅

## 涓夋閮ㄧ讲

1. **Fork 鏈粨搴?*锛堟垨鏂板缓浠撳簱鍚庢妸 `scripts/`銆乣.github/`銆乣index.html` 浼犱笂鍘伙級
2. **寮€鍚?GitHub Pages**锛氫粨搴?Settings 鈫?Pages 鈫?Source 閫?**Deploy from a branch** 鈫?鍒嗘敮 `main`銆佺洰褰?`/ (root)` 鈫?Save
3. **鎵嬪姩璺戜竴娆?*锛欰ctions 鈫?Daily Reddit Digest 鈫?Run workflow锛堜箣鍚庢瘡澶╁寳浜椂闂?08:00 鑷姩鏇存柊锛?
鍑犲垎閽熷悗璁块棶 `https://<浣犵殑鐢ㄦ埛鍚?.github.io/<浠撳簱鍚?/` 鍗冲彲鐪嬪埌褰撴棩閫熻銆?
## 鍔ㄦ€佽皟鑺傦細姣忎釜鐗堝潡鐙珛閰嶇疆

缂栬緫 `scripts/subreddits.json`锛屾瘡涓増鍧楁敮鎸佸洓涓瓧娈碉細

```json
{"name": "technology", "limit": 5,    "comments": true,  "comments_count": 8}
{"name": "programming", "limit": 2,   "comments": false}
{"name": "old_news",    "enabled": false}
```

| 瀛楁 | 鍚箟 | 榛樿 |
|---|---|---|
| `name` | 鐗堝潡鍚嶏紙涓嶅惈 r/锛?| 蹇呭～ |
| `limit` | 姣忓ぉ鎶撳嚑鏉″笘瀛愶紙鍔犲己璋冨ぇ / 鍑忓急璋冨皬锛?| 4 |
| `comments` | 鏄惁鎶撳彇楂樿禐璇勮锛堣窡甯栵級 | false |
| `comments_count` | 姣忓笘淇濈暀鍑犳潯 top 璇勮 | 5 |
| `enabled` | false 琛ㄧず褰诲簳涓嶆姄 | true |

鎯冲姞寮烘煇涓増鍧?鈫?璋冨ぇ `limit`銆佸紑 `comments`锛涙兂鍑忓急 鈫?璋冨皬 `limit`锛涗笉鎯崇湅 鈫?`enabled: false`銆?
## 鑷姩鎺㈢储锛氬彂鐜颁綘娌¤杩囩殑鐗堝潡

姣忓ぉ宸ヤ綔娴佷細鍏堣窇 `scripts/explore.py`锛氭姄 Reddit 鐑棬鐗堝潡姒滃崟 鈫?鎺掗櫎宸叉敹褰曠殑 鈫?淇濈暀 15 涓€欓€夊啓鍏?`scripts/explore.json`锛屾覆鏌撳埌椤甸潰搴曢儴**"馃攳 鎺㈢储鎺ㄨ崘"鍖?*锛堟樉绀虹増鍧楀悕銆佽闃呮暟銆佺畝浠嬶級銆?
鐪嬪埌鎰熷叴瓒ｇ殑锛屽姞涓€琛屽埌 `subreddits.json` 瀵瑰簲鍒嗙被鍗冲彲锛屾鏃ョ敓鏁堛€備篃鍙互鐩存帴鍛婅瘔鎴戯紙"鎶?r/xxx 鍔犺繘鍘?锛夈€?
## 鍙€夛細涓枃鏍囬缈昏瘧

涓嶉厤缃篃鑳界敤锛堣嫳鏂囨爣棰?+ 涓枃鐗堝潡鍚嶏級銆傛兂缈昏瘧鏍囬锛?
1. 鍘?[DeepSeek 寮€鏀惧钩鍙癩(https://platform.deepseek.com/) 娉ㄥ唽骞跺厖鍊硷紙缈昏瘧绾?400 鏉℃爣棰樺嚑鍒嗛挶/澶╋級
2. 浠撳簱 Settings 鈫?Secrets and variables 鈫?Actions 鈫?New repository secret锛氬悕绉?`LLM_API_KEY`锛屽€煎～ API Key
3. 鍙€夛細`LLM_BASE_URL`锛堥粯璁?`https://api.deepseek.com`锛夈€乣LLM_MODEL`锛堥粯璁?`deepseek-chat`锛?
## 鏈湴杩愯

```bash
python3 scripts/explore.py 15             # 鎺㈢储鏂扮増鍧楋紙鐢熸垚 explore.json锛?python3 scripts/fetch.py                  # 鎶撳彇骞剁敓鎴?index.html锛堝惈璇勮锛?python3 scripts/fetch.py --no-comments    # 鏈璺宠繃璇勮锛堥〉闈㈡洿灏忥級
LLM_API_KEY=sk-xxx python3 scripts/fetch.py   # 甯︾炕璇?```

## 鍚堣璇存槑

- 涓汉闈炲晢涓氥€佷綆棰戠巼锛堟瘡鏃?1 娆★紝绾?500 娆¤姹傦紝杩滀綆浜庡畼鏂?100 娆?鍒嗛挓鍏嶈垂棰濆害锛?- 鍙睍绀烘爣棰樸€佺畝鐭炕璇戜笌灏戦噺楂樿禐璇勮锛堟瘡鏉℃埅鏂?220 瀛楃锛夛紝涓嶆壒閲忔惉杩愭鏂?鍥剧墖/鍏ㄩ噺璇勮
- 鍏ㄩ儴閾炬帴鍥?reddit.com 鍘熷笘
- 鏁版嵁鐗堟潈褰掑師浣滆€呬笌 Reddit 鎵€鏈夛紝鏈〉闈粎渚涗釜浜哄涔犲弬鑰?
