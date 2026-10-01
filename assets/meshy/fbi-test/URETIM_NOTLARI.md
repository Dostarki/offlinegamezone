# FBI — Meshy deneme modeli

- Model: Meshy 6.
- Geometri işlemi: `01a0eff8-fa17-72b8-8c89-41cbf4b87c16` (tamamlandı, 20 kredi).
- Dokulandırma işlemi: `01a0f002-bd1d-740a-9ab5-46dfbd44e634` (tamamlandı, 10 kredi).
- Toplam tüketim: 30 kredi. İndirilen dosya: `fbi-textured.glb` (8.175.232 bayt).
- Base color, metallic, roughness, normal ve emission doku dosyaları `fbi-textured_textures/` klasöründe ayrıca kaydedildi.
- Format: GLB. T-pose; hedef 15.000 üçgen, remesh açık.
- Dokular: 2K PBR; base color üzerindeki aydınlatmayı kaldırma açık.
- Tasarım: stilize erkek FBI ajanı; lacivert üniforma, siyah taktik yelek, sarı FBI yazıları, eldivenler, botlar ve ekipman kemeri. Silah ve kaide yok.
- Bu dosya görsel değerlendirme denemesidir. Oyun entegrasyonu ve rigging henüz yapılmadı.

## İşleme devam etme

Dokulandırma durumunu Meshy `meshy_get_task_status` aracında yukarıdaki işlem kimliği ve `task_type: text-to-3d` ile kontrol et. Tamamlanınca `meshy_download_model` ile GLB dosyasını bu klasöre `fbi-textured.glb` adıyla kaydet.
