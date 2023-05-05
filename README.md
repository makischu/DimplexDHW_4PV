# DimplexDHW_4PV

This is about the combination of a domestic hot water heat pump and photovoltaic. My hot water heat pump is a Dimplex DHW 300+, but the hacks may also work for other DHW models (probably DHW 250P, DHW 300, DHW 300+, DHW 300D, DHW 300D+, DHW 301P, DHW 301P+, DHW 400+). The goal is to maximize the green energy share, and to have fun making things "smart".

![Overview](./img/dimplexoverview.jpg)

Note that there are simpler solutions. This project is also for fun, not plain efficiency. The Dimplex device offers time-dependent temperature settings, which should suffice to reschedule most of the power consumption to times of pv yield, without extra wiring. And it offers a "smart grid digital input" for even better adaption to e.g. real pv yield, requiring only a single cable to the pv system. And Dimplex offers [PV OPT](https://dimplex.de/presse/news/pv-optimizer) as another option.

Disclaimer: Dimplex is a registered trademark of Glen Dimplex UK Limited. I am not affiliated to Glen Dimplex, I am an end user. No more, no less. All my proposals are offered in the hope they may be useful. In doubt, refer to official sources only and do not modify anything. **Danger to life from electric current!**

## Similar projects and starting points 

During my search for a hot water heat pump I found some officially-looking information about Modbus on the Dimplex DHW on dimplex.de, which I rated as a big plus for the Dimplex. Unfortunately the original page disappeared later, but it is still available on [archive.org](https://web.archive.org/web/20210513144740/http://www.dimplex.de/wiki/index.php/DHW_Modbus_RTU). Furthermore you can find the complete [Installation and User Manual](https://dimplex.de/sites/default/files/downloads/Dimplex_Montageanweisung_4519056601_a_FD0102_DHW300_300_dim.pdf) online, and even [electrical documentation](https://dimplex.de/sites/default/files/DHW_300plus_Elektrodokumentation.pdf) (linked from [dimplex.de](https://dimplex.de/dimplex/warmwasser/warmwasser-waermepumpen/dhw-300plus)). Awesome! 

A distinction: We do *not* need additional Dimplex-specific hardware. We do *not* need [~~NWPM extension for ModbusTCP~~](https://dimplex.atlassian.net/wiki/spaces/DW/pages/2900361221/NWPM+Modbus+TCP+EN) or [~~Dimplex's PV-Optimizer~~](https://www.dimplex-partner.de/media/Montageanweisungen_SYS/5_Zubehoer/dimplex_PV-Opt_fd9907_de.pdf). 
<!--- A generic ModbusRTU/RS485 to ModbusTCP/Ethernet Converter is convenient. A [Shelly 1](https://www.shelly.cloud/de/products/shop/1xs1) ist helpful.-->

A distinction: This project deals with wires and other low-layer communication. If you expect to see out-of-the-box pretty visualization or generic home automation integration, you may be disappointed. But there seem to be a few interesting other projects, e.g. for [ioBroker](https://forum.iobroker.net/topic/5755/frage-dimplex-w%C3%A4rmepumpe-temperaturen-%C3%BCber-modbus-auslesen), [loxone](https://www.loxforum.com/forum/verkabelung-installation/273973-pv-anlage-mit-speicher-fronius-gen24-u-dimplex-warmwasser-w%C3%A4rmepumpe), [FHEM](https://forum.fhem.de/index.php?topic=75638.465), [NodeRED](https://kaloon.ch/2019/03/challenge-dimplex-dhw-300-brauchwasser-waermepumpe-modbus-rtu/) or [HomeAssistant](https://github.com/ChristophCaina/ha-dimplex-heatpump-modbus). Each unchecked, just hints.

## To be continued.
