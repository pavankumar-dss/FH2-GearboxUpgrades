# Gearbox Upgrades

Gearboxes with **1 to 8 forward gears** for every car in **Forza Horizon 2 on PC (Azimuth)**, bought in the Upgrade Shop like any other part. It's an [Extra Options](https://github.com/RokkuDayo/ForzaHorizon2_ExtraOptions) plugin, and it works on modded cars too.

In the Garage, go to **Upgrades > Custom upgrade > Drivetrain > Transmission**. After the car's own gearboxes you'll find a **1-Speed Gearbox** through an **8-Speed Gearbox**, leaving out the gear count the car already has. Each costs 2,000 CR (1,800 with VIP). Fit one and the car drives on it straight away, and every ratio can be tuned afterwards.

Eight is the most the game can hold: it reads at most nine gears, counting reverse.

## How the gears are chosen

- **First and top gear stay where your car has them**, so launch and top speed stay about the same. Reverse and the final drive are copied from the stock gearbox.
- **The gears between close up toward the top**, as real gearboxes do: big steps low down, small ones near the top. The curve is the median fit over 478 stock gearboxes in the game and the ZS car packs. On top of it goes half of how your car's own gearbox differs from that curve, so it keeps some of its character.
- **More gears than stock means quicker shifts.** The shift time is cut in proportion, so going from first to top takes as long in total as it did on the stock gearbox. Fewer gears keep the stock shift time.

For example, the stock Ferrari 430 Scuderia (6-speed, 0.08 s shifts) gets this 8-speed:

| Gear | 1st | 2nd | 3rd | 4th | 5th | 6th | 7th | 8th | Shift |
|---|---|---|---|---|---|---|---|---|---|
| Stock 6-speed | 3.29 | 2.16 | 1.61 | 1.27 | 1.03 | 0.82 | | | 0.08 s |
| 8-Speed Gearbox | 3.29 | 2.46 | 1.92 | 1.55 | 1.29 | 1.09 | 0.93 | 0.82 | 0.057 s |

Measured in game while coasting through the gears, the 8-speed's ratios were all within 1% of these numbers. The shop shows it as SHIFT TIME -0.02S and PI 870 → 872. The game's own figures put it 0.08 s slower from 0 to 97 km/h than stock, because closer gears mean more shifts in any given speed range.

## Requirements

| Requirement | Version tested |
|---|---|
| **Forza Horizon 2** (Xbox One version) | Build 1.0.0.64 |
| **Azimuth** | 1.0.1 |
| **[Extra Options](https://github.com/RokkuDayo/ForzaHorizon2_ExtraOptions)** by RokkuDayo | 0.4.4 |

## Install

1. Close the game.
2. Download `GearboxUpgrades-1.0.0.zip` from **Releases** and drag the `mods` folder inside it onto your Azimuth folder (the one with `azimuth.exe`). You get:

   ```
   mods\Gearbox Upgrades\mod.json
   mods\Gearbox Upgrades\database.json
   mods\Gearbox Upgrades\strings.json
   mods\Gearbox Upgrades\plugins\GearboxUpgrades.dll
   ```

3. Start the game. Extra Options turns on new mod folders by itself.

`FH2_ExtraOptions.log` beside `azimuth.exe` should then have a line like `GEARBOX UPGRADES: added 3360 gearboxes for 480 drivetrains`.

## Good to know

- **The Tune page can show the old gearbox.** After you fit a new gearbox in place of a stock one, the Tune page may still show the old ratios and acceleration times. The game does this with its own Race gearbox too. The car drives on the gearbox you bought.
- **Enhanced Tuning:** its **Top speed** slider changes the final drive of every gearbox a car has. With this mod a car has about 10, and Enhanced Tuning 1.0.0 only handles 8. With 1.0.0 the slider logs `has more rows than expected; not changed` and leaves the car alone. Everything else works. The fix is proposed in [Enhanced Tuning PR #2](https://github.com/Pantsedit/FH2-EnhancedTuning/pull/2).
- **Saves:** a car fitted with one of these gearboxes needs this mod to load it, as with any part a mod adds. Before uninstalling, put the stock gearbox back on those cars.

## Uninstall

1. Put the stock gearbox back on any car that has one of these (see above).
2. Delete `mods\Gearbox Upgrades\` and its line in `mods\loadorder.txt`.

No game file is changed. The gearboxes only exist in the game's database in memory while the game runs.

## Building

Visual Studio Build Tools (x64): `build.cmd` builds `release\Gearbox Upgrades\plugins\GearboxUpgrades.dll` and `build\run_on_copy.exe`.

Tests run the plugin against a copy of the game's database, with no game running:

```
python tests\check.py prepare "<game folder>" copy.slt
build\run_on_copy.exe "release\Gearbox Upgrades\plugins\GearboxUpgrades.dll" copy.slt
python tests\check.py verify copy.slt
```

`check.py` checks every added gearbox: its level, gear count and order, unused gears, labels, shift time, and its ratios against `tests\twin.py`, a Python copy of the formula. `tests\spacing.py` and `tests\spacing_methods.py` are the research behind the spacing.

## Credits

- **[Forza Horizon 2 Extra Options](https://github.com/RokkuDayo/ForzaHorizon2_ExtraOptions)** by Arthur (RokkuDayo), GPL-3.0. Gearbox Upgrades is an Extra Options plugin: it uses Extra Options' mod loader, its plugin API (`include\fh2_plugin.h` is Extra Options' plugin API header), and the merged in-memory game database it hands to plugins.
- **[Azimuth](https://almost-there-games.itch.io/azimuth)** by Almost There Games, which runs Forza Horizon 2 on Windows. Nothing from it is included.

Not affiliated with or endorsed by Playground Games, Turn 10 Studios, Microsoft, Almost There Games or the Extra Options author. No game files are included: you need your own copy of Forza Horizon 2.

## AI disclosure

This mod was built with Claude, Anthropic's AI assistant, which did most of the reverse engineering, code and documentation. The author directed the work and tested it in game.

## License

GPL-3.0, see [LICENSE](LICENSE). It's the same licence as Extra Options, whose plugin API header is included.
