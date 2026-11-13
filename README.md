# GeoSite RU Server

Серверный `geosite_RU.dat` содержит ровно одну категорию `RU`. Для Xray с отдельным файлом используйте `ext:geosite_RU.dat:ru`.

- [Последний релиз](https://github.com/SpeedeMiner/Geosite-ru-server/releases/tag/latest-optimized)
- [Скачать DAT](https://github.com/SpeedeMiner/Geosite-ru-server/releases/download/latest-optimized/geosite_RU.dat)
- [RAW из ветки release](https://raw.githubusercontent.com/SpeedeMiner/Geosite-ru-server/release/geosite_RU.dat)

Сборка берёт `RU` из последнего стабильного номерного релиза [Geosite-ru-light](https://github.com/SpeedeMiner/Geosite-ru-light) и сохраняет типы правил. `BLOCK` и отдельные категории Hydra не добавляются в DAT и не сливаются с `RU`. Приватные имена и новые пересечения с `BLOCK` исключаются по версионируемому списку. Старые совпадения с `BLOCK` не вычитаются из имеющегося покрытия. Десять суффиксов из предыдущей серверной базы сохранены.

## Автоматическое обновление

GitHub Actions проверяет [релизы Light](https://github.com/SpeedeMiner/Geosite-ru-light/releases) каждый час на 17-й минуте. Тот же процесс можно запустить кнопкой **Run workflow**. Сборка выбирает наибольшую стабильную версию (например, `v11.10` новее `v11.3`), пропускает черновики, prerelease и плавающий тег `latest-optimized`. Дополнительный токен и ручное обновление версии или SHA-256 не нужны.

CI сверяет SHA-256 DAT с GitHub и файлом контрольной суммы Light, затем строит только `RU` по серверной политике. Если исходный DAT не прошёл проверку или кандидат теряет покрытие относительно ветки `release`, публикация не выполняется. При успешной проверке Server публикует одноимённый номерной релиз, обновляет `latest-optimized` и ветку `release`. Неизменившиеся файлы повторно не загружаются. В описании релиза указан тег, коммит и SHA-256 исходного Light DAT.
