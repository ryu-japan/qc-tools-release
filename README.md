# QC Tools Release

Maya 向け QC ツール群の配布用リポジトリ。

## クイックスタート

手動で配置するのは **2 ファイルだけ**。残りのツールは QC Hub（ランチャー）からインストール・更新できます。

### 1. ファイルをダウンロード

| ファイル | リンク |
|---|---|
| `qc_tools_plugin.py` | [Download](https://raw.githubusercontent.com/ryu-japan/qc-tools-release/main/tools/qc_tools_plugin/qc_tools_plugin.py) |
| `qc_hub.py` | [Download](https://raw.githubusercontent.com/ryu-japan/qc-tools-release/main/tools/qc_hub/qc_hub.py) |

> リンクを右クリック →「名前を付けてリンク先を保存」でダウンロードしてください。

### 2. ファイルを配置

| ファイル | 配置先 |
|---|---|
| `qc_tools_plugin.py` | `<MAYA_USER>/plug-ins/` |
| `qc_hub.py` | `<MAYA_USER>/scripts/` |

> `<MAYA_USER>` = `C:/Users/<ユーザー名>/Documents/maya/<バージョン>`

### 3. プラグインを有効化

1. Maya を起動
2. **Windows → Settings/Preferences → Plugin Manager** を開く
3. `qc_tools_plugin` の **Loaded** にチェック（**Auto load** も推奨）

メニューバーに「**QC Tools**」メニューが追加されます。

### 4. QC Hub から他のツールをインストール

1. メニューバーの **QC Tools → QC Hub** を起動
2. 未インストールのツールは**各ツールのボタンから個別に**、または **Check for Updates → Update All でまとめて**ダウンロード・配置できます

## アップデート

QC Hub の自動更新機能で、全ツール（プラグイン含む）を一括更新できます。

1. QC Hub を起動
2. **Check for Updates** をクリック
3. 更新があれば **Update All** で一括適用

- 更新前のファイルは `.bak` として自動バックアップされます
- Maya の再起動は不要です（即時反映）

## 対象ツール

| ツール | 説明 | Download |
|---|---|---|
| qc_tools_plugin | Maya メニュープラグイン | [qc_tools_plugin.py](https://raw.githubusercontent.com/ryu-japan/qc-tools-release/main/tools/qc_tools_plugin/qc_tools_plugin.py) |
| qc_hub | QC ランチャー | [qc_hub.py](https://raw.githubusercontent.com/ryu-japan/qc-tools-release/main/tools/qc_hub/qc_hub.py) |
| uv_qc_tools | UV チェックツール | [uv_qc_tools.py](https://raw.githubusercontent.com/ryu-japan/qc-tools-release/main/tools/uv_qc_tools/uv_qc_tools.py) |
| model_qc_tools | モデルチェックツール | [model_qc_tools.py](https://raw.githubusercontent.com/ryu-japan/qc-tools-release/main/tools/model_qc_tools/model_qc_tools.py) |
| scene_cleanup_tools | シーン整理ツール | [scene_cleanup_tools.py](https://raw.githubusercontent.com/ryu-japan/qc-tools-release/main/tools/scene_cleanup_tools/scene_cleanup_tools.py) |

## リポジトリ構成

- `manifest.json` — 各ツールの最新バージョン・ダウンロード URL・SHA-256 ハッシュ
- `tools/<tool_name>/` — 各ツールの成果物（`.py`）と README