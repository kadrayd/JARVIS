# JARVIS

Independent JARVIS Desktop Application

## İndirme

En son sürüm: **3.3.0**

[JARVIS-3.3.0.zip İndir](https://github.com/kadrayd/JARVIS/releases/download/v3.3.0/JARVIS-3.3.0.zip)

Zip'i açıp `JARVIS 3.3.exe` (veya `setup.exe`) dosyasını çalıştırın. Uygulama, güncelleyici ve kamera hareket servisi kendiliğinden başlar; harici bir sayfa veya sekme açılmaz. İndirilen dosyalardaki internet işareti otomatik kaldırılır; `JARVIS-Core.exe` doğrudan çalıştırılmaz.

## Kamera / hareket
`Ayarlar › Hakkında › KAMERA / HAREKET` satırından kamerayı açıp kapatabilirsiniz. Hareket algılandığında HUD üzerinde uyarı görünür. Görüntü hiçbir yere gönderilmez; kareler arası fark yalnızca yerel olarak hesaplanır.

## Uygulama içi güncelleme

`Ayarlar › Hakkında › GÜNCELLEME` satırındaki **GÜNCELLE** düğmesi yeni sürümü kontrol eder, indirir, SHA-256 ile doğrular, `JARVIS <sürüm>` klasörüne kurar, uygulamayı otomatik yeniden başlatır ve eski JARVIS klasörlerini siler.

## Yeni sürüm yayımlama

1. `updater/build.py --build` ile `JARVISUpdater.exe`, `setup.exe` ve `JARVISVision.exe` dosyalarını derleyin.
2. `updater/build.py --source <uygulama klasörü> --version <sürüm> --output release` ile zip ve `updates.json` üretin.
3. `updates.json` dosyasını `main` dalına işleyin.
4. `v<sürüm>` etiketli bir GitHub release oluşturup zip dosyasını asset olarak yükleyin.
5. Zip'in içinde `setup.exe`, `JARVISUpdater.exe`, `version.json` ve uygulamanın `_internal` klasörü bulunmalıdır.
