# QC Tools Release

Maya 向け QC ツール群の配布用リポジトリ。

## 構成

- `manifest.json` — 各ツールの最新バージョン・ダウンロード URL・SHA-256 ハッシュ
- `tools/<tool_name>/` — 各ツールの成果物（.py）と README

## 対象ツール

| ツール | 説明 | Download |
|---|---|---|
| uv_qc_tools | UV チェックツール | [uv_qc_tools.py](https://raw.githubusercontent.com/ryu-japan/qc-tools-release/main/tools/uv_qc_tools/uv_qc_tools.py) |
| model_qc_tools | モデルチェックツール | [model_qc_tools.py](https://raw.githubusercontent.com/ryu-japan/qc-tools-release/main/tools/model_qc_tools/model_qc_tools.py) |
| scene_cleanup_tools | シーン整理ツール | [scene_cleanup_tools.py](https://raw.githubusercontent.com/ryu-japan/qc-tools-release/main/tools/scene_cleanup_tools/scene_cleanup_tools.py) |
| qc_hub | QC ランチャー | [qc_hub.py](https://raw.githubusercontent.com/ryu-japan/qc-tools-release/main/tools/qc_hub/qc_hub.py) |
| qc_tools_plugin | Maya メニュープラグイン | [qc_tools_plugin.py](https://raw.githubusercontent.com/ryu-japan/qc-tools-release/main/tools/qc_tools_plugin/qc_tools_plugin.py) |