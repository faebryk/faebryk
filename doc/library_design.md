# Library Design Considerations #

## Component Properties ##

Motivation and constraints

- components share traits and functions
- thus we want the ability to reuse definitions and functions
- a lot of traits are not inherent to a component
    - e.g not all nand gates are individual components
- physical components dont necessarily correspond 1-1 with functional components

#### Graph ####

Component   : Node  
Interface   : Node interface  
Link        : Edge  
Properties  : <>  

| => Node 	| [Interface] -> 	| Link -> 	| [Interface] 	| Node 	|
|:-------:	|:--------------:	|:-------:	|:-----------:	|:----:	|
|    p1   	|       p2       	|    p3   	|      p4     	|  p5  	|

#### LOOK AT THIS
Comp1 -> Link l1 [L:Resistive] -> Comp2  
l1 = l1.implement(Resistor(50))  
Comp1 -> Link l11 [L] -> Resistor(50) -> Link l2 [L] -> Comp2  
            EI1 -> Link l1_ [L:Resistive] -> EI2

---

class resistive(parameter, i:e 1, i:e 2, l:f:e:r link)
    def get_resistance()
        return parameter.get_value

resistor:
    self.add_traits(Resistive(i1, i2, internal_link))

cd4011:
    for i, j in pins^2
        self.add_traits(Resistive(i, j, link(i,j)))

interface i1
interface i2

links = graph.get_all_links_between(i1,i2)
resistance = 1/l for 


R0805Footprint:
    def get_kicad_fp():
        return kicad_fp("R0805")

0805_smd_resistor():
    i1, i2
    def set_resistance(param):
        self.res = param
        
    self.add_trait(has_pcb_footprint(R0805Footprint()))


cd4011:
    self.add_trait(is_powered(vcc, gnd))

fpga:
    self.logic_power_bus = i:s::c:power(pin1, pin2)
    self.gpio_power_bus = i:s::c:power(pin3, pin2)
    self.add_trait(is_powered(self.logic_power_bus))
    self.add_trait(is_powered(self.gpio_power_bus))

battery.connect_power_to(ic4011, 1)
battery.connect_power_to(ic4011.gpio_power_bus)

def connect_p..(to, index=None):
    ptraits = to.get_traits(is_powered)
    assert(len(ptraits==1) or index is not None):


### Possible Traits ###

- component traits
    - functional
        //- resistive -> parameter, 2xi:e, l:f:e:r (internal)
        //- capacitive
        //- inductive
        //- is_powered
        //    - is_powered_by_single_if -> i:e:s:c:power
    - structural
        - composite -> [components]
    - other
        - has_footprint -> footprint
        - has_type_description -> p:constant
        - has_identifier -> p:constant
        - is_netlist_component -> has_identifier
        - is_kicad_netlist_component -> is_netlist_component, has_footprint, has_type_description,


- link traits
    //- functional
    //    - electrical
    //        - resistive -> parameter
    //        - capacitive
    //        - inductive
    //    - logical
    //- structural
    //    - composite

- interface traits
    //- electrical
    //- logical
    - other
        - has_usb2
    - structural
        - composite -> [interfaces]
        - ?composite_inheriting -> [interfaces]

- parameter traits
    - constant
    - externally_controlled
    - range

- footprint traits
    - has_kicad_footprint


#### Examples ####

##### Interaces #####
- electrical
- logical

- diff_pair
    + i:s:composite         
        - A i:e
        - B i:e

- diff_pair_grounded
    + i:s:composite
        - data diff_pair
        - ref_gnd i:e

- usb_data_bus
    + i:diff_pair_grounded
    + i:o:has_usb2
        | usb <=> (data, ref_gnd)

- power
    + i:s:composite
        - hv i:e
        - lv i:e

- i2c   
    + i:s:composite
        - sda i:e
        - sdc i:e
        - low_ref_gnd i:e

- rs485
    + i:s:composite
        - AB i:s:c:diff_pair

- usb2
    + i:s:composite
        - power i:s:c:power, 
        - data i:s:c:usb_data_bus

- usb3
    + i:s:composite
        - usb2 i:usb2
        - power i:power
        - data0 i:diff_pair_grounded
        - data1 i:diff_pair_grounded
    //TODO

##### Components #####
- resistor
    - 2xi:e
    - resistance p:constant
    + c:o:has_type_description(resistance+"R")

- capacitor
    - capacitance p:constant
    + c:o:has_type_description(capacitance+"F")

- polarized_capacitor
    + c:capacitor
    - pos i:e
    - neg i:e

- unpolarized_capacitor
    + c:capacitor
    - pins 2xi:e

- diode
    - anone i:e
    - cathode i:e

- zenner_diode
    + c:diode
    - breakdown_voltage p:constant
    + c:o:has_type_description(breakdown_voltage+"V_ZD")

- signal_diode
    + c:diode

- 1N4148
    + c:signal_diode
    + c:o:has_type_description("1N4148")

- nand
    - ins 2xi:l, out i:l

- electric_nand:
    + c:nand
        | ins + i:e
        | out + i:e
    - power i:s:c:power

- cd4011
    + c:s:composite
        - 4xelectric_nand
            | power <=> power
            | ins/out <=> pins
    - power i:s:c:power
    - pins 12xi:e
    + c:o:has_type_description("cd4011")

- TI_CD4011BE
    + c:cd4011
    + c:o:has_footprint(PDIP(14))

- NXP_HEF4011B
    + c:cd4011
    + c:o:has_footprint(SOT10(8))

- Kicad_NXP_HEF4011B
    + c:nxp_hef4011b
        | footprint fp:has_kicad_footprint
    + is_kicad_netlist_component

- instance_Kicad_NXP_HEF4011B
    + c:kicad_nxp_hef4011b
    + has_identifier

// manual composition
- usb_2_0_type-c_connector
    - i:s:c:usb2
        | power <=> (vbus, gnd)
        | data <=> (d+, d-, gnd)
    - vbus i:e
    - d+ i:e
    - d- i:e
    - gnd i:e
    - cc1 + i:e
    - cc2 + i:e

// with trait
- usb_2_0_type-c_connector
    + i:o:has_usb2
    - cc1 + i:e
    - cc2 + i:e

- usb_2_0_type-a_connector
    + i:o:has_usb2

// WRONG, cannot be 2 things at the same time (usb3 has already usb2)
- usb_3_connector
    + i:o:has_usb2
    + i:o:has_usb3

// Correct
- usb_3_connector
    - i:s:c:usb3
        | usb2 <=> (power (vbus, power_gnd), usb_data_bus(d+, d-, signal_gnd))
        | power <=> (vbus, power_gnd)
        | data0 <=> usb_data_bus(d0+, d0-, signal_gnd)
        | data1 <=> usb_data_bus(d1+, d1-, signal_gnd)
    - vbus i:e
    - d+ i:e
    - d- i:e
    - power_gnd i:e
    - signal_gnd i:e
    - d0+ i:e
    - d0- i:e
    - d1+ i:e
    - d1- i:e

- powerline
    - power i:s:c:power
    - data i:s:c:differential_pair
    + c:has_power

- battery
    + c:has_power
    - power i:s:c:power

powerline.connect_power(battery)

- soc
    + power i:s:c:power

- stm32
    + c:soc

- stm32f
    + c:stm32

- stm32f7
    + c:stm32f

- stm32f767xxxxxxx(pincnt, flash, package, temp_range, options)
    + c:stm32f7
    + c:o:has_footprint(package(pincnt))

- stm32f767zit6tr
    + c:stm32f767xxxxxxx(144, 2048k, LQFP, 6, TR)

- samd
    + c:soc

- samd10
    + c:samd

---


soc:
    - mux
        - i2c
        - uart

mux:
    30 in
        - 2 i2c -> 
    5 out

soc.i2c2.connect()







### Should pins be traits instead of first class objects? ###

Pros:
- coupling of components is abstracted away
    - electrical, logical, thermal, magnetical, optical, mechanical, ...
- pin -> coupling (graph is relating couplings instead of elec cons)
- gives more flexibility for composite components (e.g relays optical switches like led + photoresistor, ...)
- some (virtual) components do not have pins (e.g. FPGA ip)

Cons:
- might be *too* flexible
    - might be quite difficult to understand
    - might be quite difficult to implement
- coupling can be modeled also differently
- lot of work to fully define real components (or impossible)

## How to go from abstract component to concrete one ##

We want to be able to create a design incremental going from a coarse level to a detailed one.
How the details are filled in might depend on the backend/exporter, e.g. a footprint might be KiCad specific.

## Implementation considerations ##
- make component more concrete by modifying component vs replace with more concrete
    - replace
        - can retain reference to old
            -> get intermediate state at a later time
            -> useful for debugging?
    - modify
        - more performant, cuz no copying?
    - can we do both/have it be configurable/abstract over it
- multi inheritance possible in python
- inheritance implies swallowing objects and returning new instances
    - how well does this compose?
- alt to inheritance: properties

## Other stuff ##
- Component snippet (e.g. enable pin).
- Abstract component aka virtual component.
- Concrete component aka real component (exist in real life).
