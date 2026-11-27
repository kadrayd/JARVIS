# JARVIS

Independent JARVIS Desktop Application

## İndirme

En son sürüm: **3.3.0**

[JARVIS-3.3.0.zip İndir](https://github.com/kadrayd/JARVIS/releases/download/v3.3.0/JARVIS-3.3.0.zip)

Zip'i açıp `JARVIS 3.3.exe` (veya `setup.exe`) dosyasını çalıştırın. Uygulama, güncelleyici ve kamera hareket servisi kendiliğinden başlar; harici bir sayfa veya sekme açılmaz. İndirilen dosyalardaki internet işareti otomatik kaldırılır; `JARVIS-Core.exe` doğrudan çalıştırılmaz.

## Kamera / hareket
`Ayarlar › Hakkında › KAMERA / HAREKET` satırından kamerayı açıp kapatabilirsiniz. Hareket algılandığında JARVIS halkası ve nişangah hareketin yönünü takip eder; yön sağa/sola/yukarı/aşağı olarak gösterilir. Görüntü hiçbir yere gönderilmez; kareler arası fark yalnızca yerel olarak hesaplanır.

## Uygulama içi güncelleme

`Ayarlar › Hakkında › GÜNCELLEME` satırındaki **GÜNCELLE** düğmesi yeni sürümü kontrol eder, indirir, SHA-256 ile doğrular, `JARVIS <sürüm>` klasörüne kurar, uygulamayı otomatik yeniden başlatır ve eski JARVIS klasörlerini siler.

## Paket

Bu depoda uygulama kaynak kodu yayımlanmaz. GitHub'dan indirilen zip yalnızca `setup.exe`, `JARVIS-Core.exe`, `JARVISUpdater.exe`, `JARVISVision.exe`, `version.json`, kurulum notu ve gerekli çalışma zamanı dosyalarını içerir. Güncelleme dosyası (`updates.json`) SHA-256 doğrulamalıdır ve uygulama içinden kontrol edilir.
