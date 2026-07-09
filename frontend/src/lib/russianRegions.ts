// Maps regions_api's numeric `Region` id (1-83, no gaps — matches Russia's
// pre-2014 federal-subject count of 83, before Crimea/Sevastopol) to a
// human-readable name, for the region picker's name-based search.
//
// IMPORTANT: despite being described as an "OKATO code", empirical testing
// (fetching a sample station's coordinates for each of the 83 ids via
// regions_api and identifying the real-world region) shows this is NOT the
// standard two-digit OKATO leading code (e.g. official OKATO for Moscow city
// is "45", this dataset's Moscow id is "44" — close but not the same table).
// It looks like a bespoke sequential numbering specific to this dataset.
// The mapping below was built by sampling one station per id and identifying
// its region from name/coordinates — most are unambiguous (city/town names
// are usually unique to one region), but a handful are flagged below as
// LOW CONFIDENCE because the sample station's location plausibly straddles
// two regions or duplicates another id's region. Spot-check these against
// GET /wmo-indexes/{wmo_index} coordinates before relying on them.
export interface RussianRegion {
  id: string;
  name: string;
}

export const RUSSIAN_REGIONS: RussianRegion[] = [
  { id: "1", name: "Алтайский край" },
  { id: "2", name: "Республика Мордовия" },
  { id: "3", name: "Тульская область" },
  { id: "4", name: "Курганская область" },
  { id: "5", name: "Республика Ингушетия" },
  { id: "6", name: "Ханты-Мансийский автономный округ — Югра" }, // LOW CONFIDENCE
  { id: "7", name: "Кировская область" },
  { id: "8", name: "Республика Коми" },
  { id: "9", name: "Костромская область" },
  { id: "10", name: "Красноярский край" },
  { id: "11", name: "Забайкальский край" },
  { id: "12", name: "Свердловская область" },
  { id: "13", name: "Волгоградская область" },
  { id: "14", name: "Иркутская область" },
  { id: "15", name: "Пермский край" },
  { id: "16", name: "Псковская область" },
  { id: "17", name: "Ростовская область" },
  { id: "18", name: "Рязанская область" },
  { id: "19", name: "Республика Адыгея" },
  { id: "20", name: "Самарская область" },
  { id: "21", name: "Республика Хакасия" },
  { id: "22", name: "Тамбовская область" },
  { id: "23", name: "Республика Татарстан" },
  { id: "24", name: "Томская область" },
  { id: "25", name: "Нижегородская область" },
  { id: "26", name: "Республика Карелия" },
  { id: "27", name: "Архангельская область" },
  { id: "28", name: "Астраханская область" },
  { id: "29", name: "Белгородская область" },
  { id: "30", name: "Брянская область" },
  { id: "31", name: "Республика Бурятия" },
  { id: "32", name: "Чеченская Республика" },
  { id: "33", name: "Челябинская область" },
  { id: "34", name: "Чувашская Республика" },
  { id: "35", name: "Тюменская область" },
  { id: "36", name: "Республика Северная Осетия — Алания" },
  { id: "37", name: "Пензенская область" },
  { id: "38", name: "Амурская область" },
  { id: "39", name: "Кабардино-Балкарская Республика" }, // LOW CONFIDENCE (Elbrus borders Karachay-Cherkessia too)
  { id: "40", name: "Краснодарский край" },
  { id: "41", name: "Курская область" },
  { id: "42", name: "Ленинградская область" },
  { id: "43", name: "Республика Марий Эл" },
  { id: "44", name: "Москва" },
  { id: "45", name: "Московская область" },
  { id: "46", name: "Мурманская область" },
  { id: "47", name: "Ненецкий автономный округ" },
  { id: "48", name: "Новгородская область" },
  { id: "49", name: "Новосибирская область" },
  { id: "50", name: "Омская область" },
  { id: "51", name: "Орловская область" },
  { id: "52", name: "Санкт-Петербург" },
  { id: "53", name: "Сахалинская область" },
  { id: "54", name: "Республика Саха (Якутия)" }, // LOW CONFIDENCE (Kolyma-highway area near Magadan border)
  { id: "55", name: "Саратовская область" },
  { id: "56", name: "Смоленская область" },
  { id: "57", name: "Ставропольский край" },
  { id: "58", name: "Республика Тыва" },
  { id: "59", name: "Тверская область" },
  { id: "60", name: "Удмуртская Республика" },
  { id: "61", name: "Калужская область" },
  { id: "62", name: "Липецкая область" },
  { id: "63", name: "Магаданская область" }, // LOW CONFIDENCE (may duplicate id 77 — spot-check)
  { id: "64", name: "Ульяновская область" },
  { id: "65", name: "Владимирская область" },
  { id: "66", name: "Вологодская область" },
  { id: "67", name: "Ярославская область" },
  { id: "68", name: "Воронежская область" },
  { id: "69", name: "Ямало-Ненецкий автономный округ" },
  { id: "70", name: "Республика Алтай" },
  { id: "71", name: "Ивановская область" },
  { id: "72", name: "Еврейская автономная область" },
  { id: "73", name: "Республика Калмыкия" },
  { id: "74", name: "Камчатский край" },
  { id: "75", name: "Ставропольский край" }, // LOW CONFIDENCE (Kislovodsk — likely duplicates id 57, spot-check)
  { id: "76", name: "Кемеровская область" },
  { id: "77", name: "Хабаровский край" },
  { id: "78", name: "Чукотский автономный округ" },
  { id: "79", name: "Республика Дагестан" },
  { id: "80", name: "Калининградская область" },
  { id: "81", name: "Оренбургская область" },
  { id: "82", name: "Приморский край" },
  { id: "83", name: "Республика Башкортостан" },
];
