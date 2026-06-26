---
name: H2 Android Conventions
description: Single source of truth for ALL H2 Android project conventions — module architecture, Kotlin style, UI/Compose, data layer, testing, and development process. Every agent working on the h2-android project must read this file before writing any code.
color: orange
emoji: 🏗️
vibe: One place for every H2 convention — update here, works everywhere.
---

# H2 Android Conventions

Apply these rules whenever working in the `/Users/tinal/H2/Android-App/h2-android` project.

---

## 1. 模組架構

### 目錄結構

```
h2-android/
├── h2android/           # Main app — ViewModel, UseCase, UI, feature packages
├── models/              # Serializable domain models (no Android dep)
├── data/                # Repository implementations (remote + local data sources)
├── core/
│   ├── analytics/       # AnalyticsExt, analytics events
│   ├── database/        # Room DAOs, Records, TypeConverters
│   ├── datetime/        # H2DateTimeUtils, DateExt, H2DateFormat
│   ├── network/         # CoroutinesManager, exception handling
│   ├── networkconfig/   # H2DomainConfig, domain management
│   ├── security/        # KeyStore, encryption
│   ├── sharedPreferences/ # Preferences classes, PreferencesExt
│   └── utils/           # H2GsonUtils, language, timezone utils
├── ui/
│   ├── res/             # String resources, StringUtils
│   ├── datetime/        # Display date/time formatters
│   ├── number/          # FloatUtils, NumberExt (Float.toDisplayString)
│   └── unit/            # Unit display (glucose, weight)
└── BaseModule/          # Legacy AndroidCore (git submodule)
```

### 各類型放置位置

| 新增類型 | 放哪裡 |
|---|---|
| Domain model（no Android dep） | `:models` |
| Room DAO / Record / TypeConverter | `:core:database` |
| Preferences class（per-feature cache） | `:core:sharedPreferences` |
| Extension `Context.xxxPreferences()` | `PreferencesExt.kt`（`:core:sharedPreferences`） |
| Date/time logic utility | `:core:datetime` |
| Date/time display formatter | `:ui:datetime` |
| Number / float display utility | `:ui:number` |
| String resource（strings.xml） | `:ui:res` |
| Analytics event / extension | `:core:analytics` |
| General utility（Gson, language） | `:core:utils` |
| Repository implementation | `:data` |
| UI display model / ViewHolder model | `:h2android` |
| Use case / Presenter / ViewModel | `:h2android` |
| ViewModel / UseCase / UI feature | `:h2android` |

### 模組邊界規則

- Feature module 不得相依另一個 feature module；共用邏輯放 `core/` 或 `data/`。
- 新 feature 放在 `core/`、`data/`、或獨立 feature module，不要直接塞進 `h2android/`。

### ProGuard Keep Rules（模組搬移時必查）

- 移動 class 到新模組時，必須 grep 原模組的 `proguard.cfg` 和所有 `*rules.pro`，找出對應的 `-keep` rules，並在新模組的 `consumer-rules.pro` 加入等效規則。遺漏此步驟會導致 release build crash。
- **同 module 內跨 package 搬移同樣需要更新 keep rules**：`-keep class com.h2.models.smarthint.** { *; }` 不覆蓋 `com.h2.models.ecmodal.*`。只要 Gson-serialized class 被搬到新 package，就必須在 `consumer-rules.pro` 補上對應的 `-keep class <new.package>.** { *; }` rule。

---

## 2. 架構設計

### MVVM + Koin DI

- **Pattern**: MVVM with Koin DI. Do not refactor existing MVP screens unless they are already being modified.
- **New screens**: `ViewModel` + Jetpack Compose + Kotlin Flow.
- **Existing MVP screens**: Leave as-is (`*Presenter` / `*Contract` with Fragment/Activity); only maintain the existing pattern when touching these files.
- Business logic lives in **Use Cases** (`*UseCase`) in the `domain` layer.
- Data flows through **Repositories** (`*Repository`) backed by Room DAOs or remote sources.
- **Image loading**: Coil in Compose screens; Glide elsewhere.

**DI (Koin)**: Six Koin modules loaded in `H2Application`:
`viewModelModule`, `repositoryModule`, `sourceModule`, `useCaseModule`, `utilsModule`, `resourceModule`
— all located under `h2android/src/main/java/com/h2/di/`.

**Koin binding rules:**
- 新增 DI binding 時，import style 必須與同檔案其他 binding 一致：用 `import` + 短類名，不要用 fully qualified name。
- Koin-registered 物件用 `get()` 不用 `newInstance()`。已有 `single`/`factory` 的類別用 `get<ClassName>()`，不要手動 `Constructor(get())` 或 `ClassName.newInstance(context)`。

### SRP 與 Class 設計

設計新 class 前必問：「這個 class 的職責是什麼？和目標 class 是同一件事嗎？」

**一律獨立成檔的類型：**

| Class 類型 | 應放位置 | 說明 |
|---|---|---|
| `sealed class`（非 UI state） | `model/` | 資料定義，與 Service 分離 |
| `data class`（domain / DTO） | `model/` | 與使用它的 Service / Presenter 分離 |
| `enum class` | `model/enums/` | 同上 |
| Service / UseCase | `feature package` | 只含邏輯，不含資料定義 |

**允許 nested class 的例外**（與 parent 語意不可分離）：
- `RecyclerView.ViewHolder`
- UI State（`sealed class UiState`，定義在對應的 ViewModel 內）
- `Builder`（只作為同 class 的建構輔助）

**禁止**：將 `sealed class`、`data class`、`enum class` 定義為 Service / Presenter / Repository 的 nested class。

### Enum Mapper 模式

當一個 discriminator 字串（如 `panelItem`、`viewType`）需要對應到多個靜態資源（`@StringRes`、`@DrawableRes`、URL template）時，用 **enum** 作為單一真相來源，不要把 resource ID 存進序列化的 data class。

**原因**：Android resource ID 在不同 build 間可能改變，存進 SharedPreferences JSON 後跨版本反序列化時會對到錯誤資源。

**情境 A — enum 本身不序列化（只存字串 key）**：Serializable model 存 `panelItem: String`，enum 留在 `:h2android` 可含 R refs。

**情境 B — serializable model 直接持有 enum（推薦）**：若 serializable model 需要直接存 enum type，enum **必須放 `:models` module 且不得含 R reference**。Gson 序列化 enum 只寫名稱（穩定跨 build）；R 對應改為 `:h2android` extension：

```kotlin
// :models module — NO R references
enum class EcModalType(val panelItem: String) {
    BG_PROBIOTICS("bgpM1"),
    DIET_FIBER("dietfM1");
    companion object { fun fromPanelItem(p: String) = entries.firstOrNull { it.panelItem == p } }
}

// :h2android module — R references 在這裡
fun EcModalType.toDisplayResources() = when (this) {
    EcModalType.BG_PROBIOTICS -> EcModalTypeResources(R.string.ec_modal_bgp_body, ...)
    EcModalType.DIET_FIBER    -> EcModalTypeResources(R.string.ec_modal_diet_body, ...)
}
```

> **常見錯誤**：enum 在 `:h2android`（含 R refs）但 serializable model 在 `:models` 直接持有該 enum type → 編譯失敗（module 邊界衝突）。情境 B 必須把 enum 移到 `:models` 去掉 R refs。

---

## 3. Kotlin 程式規範

### 命名規範

- **檔名 / 類別**：UpperCamelCase；繼承 Android component 的類名以 component 名結尾（例：`SignInActivity`、`UserProfileFragment`）。
- **資源檔名**：lowercase_underscore（例：`activity_user_profile.xml`、`ic_star.png`）。
- **字串與 key 前綴**：SharedPreferences `PREF_`、Bundle `BUNDLE_`、Fragment ARG `ARGUMENT_`、Intent EXTRA `EXTRA_`、`ACTION_`、`REQUEST_` 等。
- **Discriminator / type string**（`viewType`、`type`、`status`、`action` 等用來區分行為的字串）一律抽成 `companion object` constants 或獨立 `object`，不得各處 hardcode 相同字串值；寫第一個 string literal 時就應立即建立 constant。
- **Companion object 常數用 SCREAMING_SNAKE_CASE**：`private const val DIALOG_WIDTH_RATIO`，不是 `DialogWidthRatio`。
- **Constant 值要語意清楚**：`VALUE_EC_PROMO` 而非 `VALUE_EC`（太模糊）。
- **XML view ID 遵循既有命名慣例**：先看同一個 layout 其他元件的命名模式再決定。
- **Enum 命名反映角色，不反映型別**：名稱描述「這個 enum 在結構裡的位置/角色」，不描述「它存了什麼型別的資料」（e.g., `EcHintBloodGlucoseLeadText` → `EcHintBloodGlucoseLead`）。
- **`Map<K, V>` 型別屬性名稱要與 `List` 型別有所區分**：`Pool` 後綴暗示 `List`（可直接 `.random()`）。若實際型別是 `Map`，名稱應加 `Map` 或語意 key 後綴（如 `ByCalorie`）。

### Class 成員排序

Class body 內的成員依下列順序排列：

1. `abstract val` / `abstract var`
2. `abstract fun`
3. `public val` / `public var`（含 `internal`）
4. `private val` / `private var`（含 `protected`）
5. `companion object { }`
6. `init { }`
7. `override fun`
8. `public fun`（含 `internal`）
9. `protected fun`
10. `private fun`
11. `private class`
12. `private interface`

**Sealed Class 特別規則**：`abstract` 屬性排在 `concrete` 屬性之前。

Review 時必須對 diff 裡每個新增成員逐條核對其在 class 內的實際位置是否符合此順序，不能只做整體印象掃描。

### Null Safety

- **禁用 `!!` force unwrap**。
- 多狀態條件（3 個以上分支）優先用 `when` 而非巢狀 `if`，讓每個狀態一目了然且可受 smart cast 保護。
- **新增 discriminator type 時，必須明確在 `when` 中列出**，即使行為和 `else` 完全相同也要列出，以表達「此 type 已被考慮」的意圖。不能讓新 type 隱性 fall-through 到 `else`。
- 在 constructor parameter 或 property 加 `?` 前，必須追到來源確認實際回傳型別。若 factory method / DI module 已保證 non-null，`?` 是多餘的。

### Coroutines & Dispatcher 分層

每個 layer 的 threading 由自己負責，判斷依據是**職責**，不是「底層技術上會不會 block」：

| Layer | 職責 | 預設 dispatcher |
|---|---|---|
| Repository | 資料 I/O（SharedPreferences、DB、網路） | `Dispatchers.IO` |
| Use case | 業務邏輯、mapping、computation | `Dispatchers.Default` |
| Presenter / ViewModel | UI state 更新 | `Dispatchers.Main` |

- Repository interface 方法宣告為 `suspend`。
- Dispatcher 透過建構子注入，**不得在 method body hardcode**：

```kotlin
// ❌ 無法在測試中替換
override suspend fun get(...) = withContext(Dispatchers.IO) { ... }

// ✅
class RepositoryImpl(
    private val dispatcher: CoroutineDispatcher = Dispatchers.IO
) {
    override suspend fun get(...) = withContext(dispatcher) { ... }
}
```

- 常犯錯：「SharedPreferences `apply()` 是 async，所以 repository 不需要切 IO」→ **錯誤**。Layer 職責才是判斷依據。
- 常犯錯：在已跑在 IO thread 的 suspend function 內再多包一層 `withContext(Dispatchers.IO)`。

### Data Class 設計

- **影響 `equals`/`hashCode` 的屬性必須放進 constructor，不能定義在 class body 裡**。`data class` 的 `equals`/`hashCode` 只比較 constructor 參數；body 裡的 `val` 不計入。
- 正確作法：把需要參與比較的屬性改為 `abstract val`，在 data class constructor 中 `override` 並傳入值。

### Fragment Arguments

- **Fragment args 優先用 `by lazy`，不用 `lateinit var` + `onCreate` 初始化**：

```kotlin
// prefer
private val ecModalType: EcModalType by lazy { requireArguments().getSerializable(ARG_EC_MODAL_TYPE) as EcModalType }
// avoid
private lateinit var ecModalType: EcModalType
override fun onCreate(...) { ecModalType = requireArguments()... }
```

### Extension Import

`viewModelScope`（extension property）、`launch`（extension function）等都必須在每個檔案各自 import，parent class 的 import 不會傳遞給子類別。

### 其他規範

- 例外處理：不得忽略例外；避免捕捉通用 `Exception`；避免 `import *`。
- 新 code 用 Coroutines + Flow 處理非同步；LiveData 只保留在現有 MVP 畫面。
- **不用 `sed` 改 Kotlin 檔案**：macOS `sed -i ''` 遇到含括號的 pattern 會靜默清空檔案。一律用 Edit tool 修改，修改後 stage 前確認檔案有內容。
- Suspend if/else > 10 行需評估抽 wrapper，避免重複的 shimmer/loading 控制邏輯。

---

## 4. UI / Compose 規範

### Design System — Figma token 對應 H2Theme

Jira ticket 有 Figma 連結時，必須用 Figma MCP (`get_design_context`) 讀取後再實作。

從設計稿取得 token 後，**對應到專案已定義的 H2Theme**，不得 hardcode 數值：

| Figma token 類型 | 對應到 |
|---|---|
| Typography（如 `Title/Primary Heading/Android`） | `H2Theme.typography.*` |
| Spacing / Size | `H2Theme.spacing.*` |
| Color | `H2Theme.color.*` |
| Corner radius | `H2Theme.radius.*` |

若設計稿 token 名稱找不到對應的 H2Theme 值，先問使用者，不要用 hardcode 數值替代。

**Design Token 範例：**

| Token | 範例 |
|---|---|
| Color | `H2Theme.color.primary`、`.gray100~900`、`.warningOrange`、`.inRange` |
| Typography | `H2Theme.typography.titlePrimaryHeading`、`.contentPrimary`、`.buttonPrimary` |
| Spacing | `H2Theme.spacing.small`(8dp)、`.medium`(16dp)、`.large`(24dp) |
| Radius | `H2Theme.radius.defaultRadius`(8dp)、`.dashboardCardRadius`(10dp) |

Color 不用 hardcode hex：`Color(0xFFF7F7F6)` → 查 `H2ColorLightTokens` 找語意最接近的 token（例：淺灰背景 `#F7F7F6` → `H2Theme.color.gray100`）。Color alpha 用 `H2Theme.color.xxx.alpha80`（`H2ColorExt.kt`）。

### CompositionLocal 限制

`H2Theme.radius.*`、`H2Theme.spacing.*`、`H2Theme.color.*` 是 CompositionLocal，**只能在 `@Composable` 函式內讀取**。不可用 top-level `val` 或 object property 持有：

```kotlin
// ❌
private val ContentShape = RoundedCornerShape(H2Theme.radius.defaultRadius)

// ✅
@Composable
private fun MyCard() {
    val shape = RoundedCornerShape(H2Theme.radius.defaultRadius)
    ...
}
```

同一個 shape / spacing 值在同一個 Composable 內多次使用時，宣告一次 local val，不要重複呼叫三次。

### 共用元件（優先使用）

專案已有一套 H2 設計系統元件，**優先使用**，非必要不自製：

`H2Button`、`H2ButtonWithIcon`、`H2OutlinedButton`、`H2TextButton`、`H2ButtonBottomBar`、`H2TextField`、`H2Toolbar`、`H2Divider`（`H2HorizontalDivider`）、`H2AlertDialog`、`H2ImageDialog`、`ProgressDialog`、`H2Tooltip`、`H2WheelDatePicker`、`H2TextWithIcon`

### ComposeView 使用

專案已有 `ComposeViewExt.setupDefaultStrategy()` 統一封裝 `DisposeOnViewTreeLifecycleDestroyed` 策略：

```kotlin
import com.h2.baselib.ui.extension.setupDefaultStrategy

binding.myComposeView.setupDefaultStrategy()  // ✅

// ❌ 繞過共用 extension，不要這樣寫：
// binding.myComposeView.setViewCompositionStrategy(
//     ViewCompositionStrategy.DisposeOnViewTreeLifecycleDestroyed
// )
```

### ConstraintLayout Margin

ConstraintLayout 的 margin 只在對應方向有 constraint 時才生效：

```xml
<View
    android:layout_marginBottom="@dimen/small"
    app:layout_constraintBottom_toBottomOf="parent"   <!-- 必須有這行，bottom margin 才生效 -->
    app:layout_constraintTop_toBottomOf="@id/prev" />
```

### URL / Link 開啟（3 種情況）

1. **外部瀏覽器**：`context.openExternalBrowser(url)`（`com.h2.utils.AppUtils`）
2. **App 內 WebView**：
   ```kotlin
   context.checkNetwork {
       context.startActivity(PartnerWebActivity.getIntent(context = context, linkUrl = url))
   }
   ```
3. **H2Protocol（h2scheme）**：`H2Protocol(context).execute(url)`（判斷：`H2Protocol.isH2Protocol(url.toUri())`）

判斷優先順序：h2scheme → 外部瀏覽器 → 內部 WebView。不確定時先問使用者。

**Compose inline clickable text**：用 `LinkAnnotation.Clickable` + `withLink`，不要用已 deprecated 的 `ClickableText`。

---

## 5. 資料層規範

### Gson / @SerializedName

**`@SerializedName` 只在欄位名稱 ≠ JSON key 時才需要加。**

新增 data class 欄位前，先確認：
1. 該 class 所在 package 是否已在 `models/consumer-rules.pro` 有 `-keep class com.package.** { *; }` 規則
2. 若有，且欄位名稱與 JSON key **完全一致**，不要加 `@SerializedName`

```kotlin
// ✅ 欄位名和 JSON key 一致，已有 keep rule
data class DashboardSummaryEntry(val epochDay: Long)

// ✅ Enum entry 識別碼和 JSON value 不同 → 必須加
@SerializedName("cgmmA1") CGMM_A1("cgmmA1")

// ❌ 多餘（欄位名 = JSON key，且有 keep rule）
@SerializedName("epochDay") val epochDay: Long
```

### Room / SQLCipher

- **Room** 使用 SQL Cipher 加密（production）；schema version 在 `h2android/build.gradle.kts`。
- **KSP**：用於 Room schema export 和 Koin annotation 驗證。
- Migration 測試放在 `test/junit`。

### SharedPreferences

**Preferences 命名：** `H2_PREFS + "FeatureName"`，不要 hardcode `"H2_FeatureName"`：

```kotlin
private const val PREFERENCES_NAME = H2_PREFS + "DashboardSummary"  // ✅
private const val PREFERENCES_NAME = "H2_DashboardSummary"           // ❌
```

**⚠️ Logout cleanup（常被忽略）：** 每個新增的 SharedPreferences 必須在 `LocalDataUseCase.clearPreferences()` 加入 `.clear()`。遺漏會導致換帳號時仍看到前一個 user 的 cache（privacy issue）。

**Repository 邊界**：Repository impl 不應直接呼叫 `preferences.builder().all.keys` 等 Preferences 內部方法（`builder()` 設計上供 factory 子類別在自身內部使用）。key 解析邏輯屬於 Preferences 層，repository 只做一行 delegation。

---

## 6. 現有可重用資源

**設計前：先問「現有有沒有可以用的？」**

收到任何功能需求時，在提出任何新結構之前先做探索：

1. **新 data class / field** → 先找現有 data class 是否能加欄位
2. **新 service method** → 先看現有 service 是否已有類似邏輯
3. **新 utility / helper** → 先 grep 是否已有同用途的 util
4. **新 SharedPreferences key** → 先確認現有 preferences object 有沒有語意上相符的 group

每個擬新增的結構，在 proposal / tasks 中必須說明為何現有程式碼不足，不能只說「新增 X」而不提是否考慮過現有選項。

**常用工具速查：**

| 需求 | 用這個，不要自己寫 |
|---|---|
| 判斷某個 timestamp 是否為今天 | `H2DateTimeUtils().isToday(timestamp)` |
| Float 四捨五入到 N 位 | `FloatUtils.round(value, places)` |
| 數字顯示格式 | `Float?.toDisplayString(n)`（`ui/number/NumberExt.kt`） |
| JSON | `H2GsonUtils`（`core/utils`） |
| Analytics event | `"event".sendEvent()`（`core/analytics/AnalyticsExt.kt`） |
| View 顯示/隱藏 | `.visible()` `.gone()`（`BaseModule/ViewExt.kt`） |
| 開啟外部連結 / WebView / H2 protocol | 見第 4 節「URL / Link 開啟」 |

### `:models` module（`com.h2.models.*`）

| Domain | 主要 class / enum | Package |
|---|---|---|
| User | `User`、`DiabetesType`、`DiseaseType`、`GenderType` | `com.h2.models.user` |
| SmartHint | `SmartHintInfo`、`SmartHintLastTime`、`SmartHintActionButtonInfo`、`SmartHintViewType`、`EcModalType`、`DietFiberLevel` | `com.h2.models.smarthint` |
| Diary | `DiaryPhoto`、`@DiaryItemType` | `com.h2.models.diary` |
| Unit / Measurement | `BloodGlucoseValue`、`Height`、`Weight`、`HeightUtils` | `com.h2.models.unit` |
| Lab Data | `LabData`、`LabDataType`、`LabDataRange`、50+ 檢驗項目 | `com.h2.models.labdata` |
| Titration | `Survey`、`LogHistory`、`SurveyDoseInfo` | `com.h2.models.titration` |
| Premium | `PremiumContent`、`CollectionType` | `com.h2.models.premium` |

### Utilities

| 類別 | Class | 備註 |
|---|---|---|
| 日期時間 | `H2DateTimeUtils`、`H2DateFormat`、`DateExt`、`H2CalendarExt` | `core/datetime` |
| JSON | `H2GsonUtils`、`DateDeserializer` | `core/utils` |
| 語系 | `H2WebUrlLangTag`、`H2ApiLangTag`、`MultiLanguageSupport` | `core/utils/language` |
| 字串 | `StringUtils`、`StringFormatUtils`、`H2StringUtils` | |
| 數值 / 單位 | `DoubleUtils`、`BMIUtils`、`H2UnitUtils`、`WeightUtils`、`FloatUtils` | |
| 網路 | `H2NetworkUtils` | |
| 資源存取 | `H2ResourcesUtils`、`StringResourceProvider` | |
| SharedPreferences | `H2PreferenceUtils`、`PreferenceDB` | |
| App / URL | `AppUtils`（含 `openExternalBrowser`） | |

### Extension Functions（依情境查詢）

| 情境 | Extension | 來源檔 |
|---|---|---|
| View 顯示隱藏 | `.visible()` `.gone()` `.fadeIn()` `.fadeOut()` | `ViewExt.kt`（BaseModule） |
| Compose 點擊 / 動畫 | `Modifier.clickableRipple()` `.noEffectClick()` `.shimmerEffect()` | `ModifierExt.kt` |
| Fragment flow 訂閱 | `launchWhenStarted {}` `observeFlowsWhenStarted {}` | `FragmentExt.kt` |
| Bundle / Intent 安全取值（API 33+） | `bundle.parcelable<T>()` `bundle.serializable<T>()` | `ParcelableExt.kt` / `SerializableExt.kt` |
| 日期計算 | `Date.toLocalDate()` `LocalDate.tomorrow()` | `DateExt.kt` |
| 數字格式化 | `Float?.toDisplayString(n)` `toDisplayStringWithSign()` | `NumberExt.kt`（ui/number） |
| Color alpha | `H2Theme.color.xxx.alpha80` `.alpha50`… | `H2ColorExt.kt` |
| Analytics | `"event_name".sendEvent()` `"screen".sendScreenName()` | `AnalyticsExt.kt` |
| 例外紀錄 | `throwable.record()` `"msg".recordAsError()` | `ExceptionRecordExt.kt` |
| Context → 偏好設定 | `context.settingsPreferences()` `.diaryPreferences()` 等 13 個 | `PreferencesExt.kt` |
| SpannableString 點擊 | `SpannableString.setKeyWordClickableSpan()` | `SpannableStringExt.kt` |
| List 變異 | `list.setAll()` `.updateItemBy()` `.replaceWith()` | `IterableExt.kt` |
| Glucose / Weight 顯示 | `Float.displayGlucoseValue()` `.displayWeightValue()` | `SettingsExt.kt` |

### Base Classes

| Class | 路徑 |
|---|---|
| `BaseActivity` | `AndroidCore/BaseModule/…h2.com.basemodule.activity` |
| `BaseFragment` | `AndroidCore/BaseModule/…h2.com.basemodule.fragment` |
| `BaseRecyclerViewAdapter` / `ViewHolder` | `AndroidCore/BaseModule/…h2.com.basemodule` |

### Validators

`EmailValidator`、`PhoneNumberValidator`、`WeightValidator`、`CaloriesValidator`、`LimitNumberValidator`、`RangeNumberValidator`、`PatternValidator`（`com.cogini.h2.utils.validator`）

---

## 7. 測試規範

- **框架**：MockK（不用 Mockito）。
- **Pattern**：AAA（Arrange / Act / Assert）— 每個測試都要有清楚的三段分隔。
- 單元測試檔案路徑對應 source path，放在 `src/test/` 下的 `com/h2/unit/...`。
- ViewModel、UseCase、Repository 的 public 方法需有單元測試；使用 `runTest`。
- **Migration 測試**放在 `test/junit`。
- 有 N 個狀態分支的邏輯，必須有 N 個對應的 test case。不能只測 happy path，每個非預設狀態都需要獨立覆蓋。
- 新功能完成後執行：`./gradlew h2android:testAlphaDebugUnitTest --tests "com.h2.unit.*"`

---

## 8. 功能整合

### Firebase Analytics

- **不重複送 USER_ID 作為 event parameter**：Firebase SDK 已有 `setUserId()` 機制，event 本身不需要再附 `USER_ID` parameter。
- **Firebase 服務**：Auth、Messaging、Analytics、Performance、Crashlytics、Remote Config。

### Drawable 命名與匯出

**命名規則：**

| 類型 | 格式 | 範例 |
|---|---|---|
| Smart Hint icon | `icon_smart_hint_<desc>_<color>.webp` | `icon_smart_hint_warning_orange.webp` |
| 內容圖片（modal、dialog） | `img_<feature>_<desc>.webp` | `img_ec_modal_probiotics.webp` |

Smart Hint icon 放在 `drawable-xhdpi/`、`drawable-xxhdpi/`、`drawable-xxxhdpi/` 三個 density folder（不放 `drawable/`）。

**PNG / JPEG → WebP 轉換：**

```bash
cwebp -q 90 /path/to/image.png -o h2android/src/main/res/drawable-xxxhdpi/image.webp
```

品質預設 q 90；檔名沿用原始檔名，只換副檔名為 `.webp`。

**既有 Smart Hint icons（勿重複新增）：**
- `icon_smart_hint_warning_orange` → 高血糖 / 高血壓警示
- `icon_smart_hint_warning_purple` → 低血糖 / 低血壓警示
- Program hint 用 Lottie JSON（`smart_hint_clap.json`、`smart_hint_star.json`、`smart_hint_party_popper.json`）

### Product Flavors

| Flavor | Application ID | 用途 |
|--------|---------------|------|
| `alpha` | `com.h2.health2sync.alpha` | 內部測試 |
| `beta` | `com.cogini.h2` | Beta 測試 |
| `prod` | `com.h2sync.android.h2syncapp` | 正式版 |

API 環境由 `api_environment` resource value 控制（prod=0, beta=1, alpha=2）。

### 重要慣例

- **Locale 支援**：Arabic、Japanese、Korean、zh-CN、zh-TW、zh-SG、en-AU。
- **Key Feature Packages**（`h2android/` 下）：`diary`、`food`、`exercise`、`measurement`、`medication`、`settings`、`profile`、`chat`、`payment`、`cgm`、`nhi`、`kenpo`、`conference`、`titration`、`recognition`、`widget`、`notification`。

---

## 9. 開發流程

### OpenSpec 同步

**spec.md 含有 state machine 或 enum 狀態時，必須覆蓋所有 state × 條件組合**，不能讓某個組合靠 implementer 自己推斷。

**openspec 文件只描述最終行為，不記錄變更歷程**：`spec.md`、`design.md`、`tasks.md` 都是「系統最終狀態」的描述。不要寫「原本是 X，改為 Y」、「此版本新增」等演化說明——那些屬於 PR description 或 commit message。

```
❌ - [x] 將 isVisible: Boolean 改為 State enum（原設計為 Boolean）
✅ - [x] cache entry 用 State enum（VISIBLE / INELIGIBLE / DISMISSED）
```

**開發中發現 pivot → 只改 openspec，不動 brainstorm**。若實作過程中有設計調整，必須在同一個 PR 同步更新 `tasks.md`、`spec.md`、`design.md`。

PR 提交前確認：`git diff origin/<base> -- openspec/` 是否有 spec 文件與 code 同步變動。

### 暫時 hardcode 字串免審規則

- `"#文字內容"` 形式的 hardcode 在活躍開發階段可免審（只適用於 `^#` 開頭的字串）。
- PR 描述須標明為暫時，並附 TODO + ticket（例：`// TODO: replace with string resource (H2S-XXXX)`）。
- 若 `#` 開頭的 hardcode 字串遺留至合併到 release/main 分支，審查者應標記為 🟡 Suggestion 或 🔴 Blocker。

### 設計前確認現有

- **Companion Object 設計 — YAGNI**：新增 companion object 方法前，先確認有 caller（`git grep -n "methodName" -- "*.kt"`）。沒有呼叫點 → 不要加。
- **Zero-callsite code**：任何新增的 code unit（function、`@Composable`、class、companion object method），若 codebase 中完全沒有 call site，應刪除。不以「以後可能用到」為由保留。

### 永遠不刪 KDoc

**永遠不刪現有 KDoc 或 block comment**（`/** ... */`、`// ===` 區塊）——改寫或遷移檔案時一律保留原文。

### 不確定時先問

遇到多種可行實作方式、設計不明確、或行為規格不完整時，先列出問題問使用者，不要假設後直接實作。
