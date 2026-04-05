# QC Tools Plugin

Maya のメニューバーに「QC Tools」メニューを追加するプラグイン。Plugin Manager から ON/OFF・autoload を管理できる。

## セットアップ

1. `qc_tools_plugin.py` を Maya の `plug-ins/` フォルダに配置
2. 各ツール本体（`.py`）を `scripts/` フォルダに配置
3. Maya の **Plugin Manager** で `qc_tools_plugin` を有効化

---

## メニュー構成

メニューバーに **QC Tools** メニューが追加される（Tear-off 対応）。

| メニュー項目 | 説明 |
|---|---|
| QC Hub | QC ツールランチャー |
| — | （区切り線） |
| UV QC Tools | UV 品質チェック |
| Model QC Tools | モデル品質チェック |
| Scene Cleanup Tools | シーン整理チェック |

---

## 互換性

Maya 2018 / 2023 / 2025（Python 2.7 / 3）対応。
