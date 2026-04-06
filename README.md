# QC Tools Release

Maya 向け QC ツール群の配布用リポジトリ。

## 構成

- `manifest.json` — 各ツールの最新バージョン・ダウンロード URL・SHA-256 ハッシュ
- `tools/<tool_name>/` — 各ツールの成果物（.py）と README

## 対象ツール

各リンクを右クリックし「名前を付けてリンク先を保存」でダウンロードしてください。

| ツール | 説明 | Download |
|---|---|---|
| uv_qc_tools | UV チェックツール | [uv_qc_tools.py](https://raw.githubusercontent.com/ryu-japan/qc-tools-release/main/tools/uv_qc_tools/uv_qc_tools.py) |
| model_qc_tools | モデルチェックツール | [model_qc_tools.py](https://raw.githubusercontent.com/ryu-japan/qc-tools-release/main/tools/model_qc_tools/model_qc_tools.py) |
| scene_cleanup_tools | シーン整理ツール | [scene_cleanup_tools.py](https://raw.githubusercontent.com/ryu-japan/qc-tools-release/main/tools/scene_cleanup_tools/scene_cleanup_tools.py) |
| qc_hub | QC ランチャー | [qc_hub.py](https://raw.githubusercontent.com/ryu-japan/qc-tools-release/main/tools/qc_hub/qc_hub.py) |
| qc_tools_plugin | Maya メニュープラグイン | [qc_tools_plugin.py](https://raw.githubusercontent.com/ryu-japan/qc-tools-release/main/tools/qc_tools_plugin/qc_tools_plugin.py) |

## インストール

### 方法 1: 手動配置

各 `.py` ファイルをダウンロードし、Maya の所定フォルダに配置してください。

| ファイル | 配置先 |
|---|---|
| `uv_qc_tools.py` / `model_qc_tools.py` / `scene_cleanup_tools.py` / `qc_hub.py` | `C:/Users/<ユーザー名>/Documents/maya/<バージョン>/scripts/` |
| `qc_tools_plugin.py` | `C:/Users/<ユーザー名>/Documents/maya/<バージョン>/plug-ins/` |

`qc_tools_plugin.py` の有効化:

1. Maya を起動する
2. **Windows → Settings/Preferences → Plugin Manager** を開く
3. `qc_tools_plugin` の **Loaded** にチェックを入れる
4. 次回以降の自動読み込みには **Auto load** にもチェックを入れる

### 方法 2: QC Hub からアップデート

QC Hub の自動更新機能を使えば、手動配置なしでツールの更新・新規取得ができます。

1. QC Hub を起動する
2. **Check for Updates** をクリックする
3. 更新があれば **Update All** で一括適用する

- 各ツールは QC Hub と同じ `scripts/` フォルダに自動配置されます
- 更新前のファイルは `.bak` として自動バックアップされます
- Maya の再起動は不要です（即時反映）

> **注意:** `qc_tools_plugin.py` は自動更新の対象外です。手動で `plug-ins/` に配置してください。