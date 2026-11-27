# JARVIS

Independent JARVIS Desktop Application

## İndirme

En son sürüm: **3.2.0**

[JARVIS-3.2.0.zip İndir](https://github.com/kadrayd/JARVIS/releases/download/v3.2.0/JARVIS-3.2.0.zip)

Zip'i açıp `JARVIS 3.2.exe` (veya `setup.exe`) dosyasını çalıştırın. Uygulama ve güncelleyici kendiliğinden başlar; harici bir sayfa veya sekme açılmaz. İndirilen dosyalardaki internet işareti otomatik kaldırılır; `JARVIS-Core.exe` doğrudan çalıştırılmaz.

## Uygulama içi güncelleme

`Ayarlar › Hakkında › GÜNCELLEME` satırındaki **GÜNCELLE** düğmesi yeni sürümü kontrol eder, indirir, SHA-256 ile doğrular, `JARVIS <sürüm>` klasörüne kurar, uygulamayı otomatik yeniden başlatır ve eski JARVIS klasörlerini siler.

## Yeni sürüm yayımlama

1. `updater/build.py --build` ile `JARVISUpdater.exe` ve `setup.exe` dosyalarını derleyin.
2. `updater/build.py --source <uygulama klasörü> --version <sürüm> --output release` ile zip ve `updates.json` üretin.
3. `updates.json` dosyasını `main` dalına işleyin.
4. `v<sürüm>` etiketli bir GitHub release oluşturup zip dosyasını asset olarak yükleyin.
5. Zip'in içinde `setup.exe`, `JARVISUpdater.exe`, `version.json` ve uygulamanın `_internal` klasörü bulunmalıdır.
