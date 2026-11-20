# GeoSite RU Server

Серверный `geosite_RU.dat` содержит ровно одну категорию `RU`. Для Xray с отдельным файлом используйте `ext:geosite_RU.dat:ru`.

- [Последний релиз](https://github.com/SpeedeMiner/Geosite-ru-server/releases/tag/latest-optimized)
- [Скачать DAT](https://github.com/SpeedeMiner/Geosite-ru-server/releases/download/latest-optimized/geosite_RU.dat)
- [RAW из ветки release](https://raw.githubusercontent.com/SpeedeMiner/Geosite-ru-server/release/geosite_RU.dat)

Сборка берёт `RU` из [Geosite-ru-light](https://github.com/SpeedeMiner/Geosite-ru-light) и сохраняет типы правил. `BLOCK` и отдельные категории Hydra не добавляются в DAT и не сливаются с `RU`. Приватные имена, новые пересечения с `BLOCK` и явно согласованные исключения из DIRECT заданы в [серверной политике](data/exclude-server-suffixes.txt). Старые совпадения с `BLOCK` не вычитаются из имеющегося покрытия. Десять суффиксов из предыдущей серверной базы сохранены.

## Автоматическое обновление

GitHub Actions проверяет [релизы Light](https://github.com/SpeedeMiner/Geosite-ru-light/releases) каждый час на 17-й минуте. Процесс также запускается после обновления `main` Server или вручную через **Run workflow**.

| Канал Server | Источник Light | Что обновляется |
| --- | --- | --- |
| Плавающий | [`latest-optimized`](https://github.com/SpeedeMiner/Geosite-ru-light/releases/tag/latest-optimized), даже если номерная версия не менялась | Server `latest-optimized` и ветка `release` для [Raw](https://raw.githubusercontent.com/SpeedeMiner/Geosite-ru-server/release/geosite_RU.dat) и [jsDelivr](https://cdn.jsdelivr.net/gh/SpeedeMiner/Geosite-ru-server@release/geosite_RU.dat). |
| Номерной | Последний стабильный номерной релиз | Новый одноимённый номерной релиз Server. Уже выпущенные версии не перезаписываются. |

Каналы проверяются и публикуются независимо. Для каждого CI сверяет DAT и файл контрольной суммы с SHA-256 из GitHub Releases, применяет серверную политику и сравнивает покрытие с уже опубликованным снимком **того же канала**. Потери покрытия без явно согласованного исключения останавливают публикацию. Неизменившиеся файлы повторно не загружаются. В описании выпуска фиксируются коммит и SHA-256 входного Light DAT.

Исторический `v11.21` сохраняется без изменений. [Исключение `habr.com`](docs/habr-rolling-sync.md) остаётся частью серверной политики.
