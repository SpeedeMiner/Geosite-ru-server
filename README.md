# GeoSite RU Server

Серверный `geosite_RU.dat` содержит ровно одну категорию `RU`. Для Xray с отдельным файлом используйте `ext:geosite_RU.dat:ru`.

- [Последний релиз](https://github.com/SpeedeMiner/Geosite-ru-server/releases/tag/latest-optimized)
- [Скачать DAT](https://github.com/SpeedeMiner/Geosite-ru-server/releases/download/latest-optimized/geosite_RU.dat)
- [RAW из ветки release](https://raw.githubusercontent.com/SpeedeMiner/Geosite-ru-server/release/geosite_RU.dat)

Сборка берёт `RU` из зафиксированного релиза [Geosite-ru-light](https://github.com/SpeedeMiner/Geosite-ru-light) и сохраняет типы правил. `BLOCK` и отдельные категории Hydra не добавляются в DAT и не сливаются с `RU`. Приватные имена и новые пересечения с `BLOCK` исключаются по версионируемому списку. Старые совпадения с `BLOCK` не вычитаются из имеющегося покрытия. Десять суффиксов из предыдущей серверной базы сохранены.

## Обновление

Обновите тег, коммит и SHA-256 Light в `data/light-source.json`. Проверьте списки исключений и сохраняемых серверных суффиксов, сравните покрытие с предыдущей базой и зафиксируйте SHA-256 результата. CI сверяет обе суммы и публикует только после успешных тестов на `main`. Автоматического перехода на непроверенный релиз Light нет.

Локальная проверка с уже скачанным входным DAT:

```sh
python3 -m unittest discover -s tools -v
python3 tools/project_geosite.py light.dat dist
(cd dist && sha256sum -c geosite_RU.dat.sha256sum)
```
