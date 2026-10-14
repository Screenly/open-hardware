# Assembly Part Library Standard

The parts used to assemble and ship a Screenly product that are not designed in KiCad.

## Assembly Part Library

The Assembly Part Library contains parts that are not part of a KiCad design: board-level products such as bare PCBs and programmed parts, mechanical parts, and everything that ships with the product.

Assembly parts differ from parts in the [Screenly KiCad Part Library](part-library-standard.md):

- They have no KiCad symbols and no footprints.
- They have no `DesignConstraint` and no parameter matching. Each assembly part is selected directly by its Screenly part number.
- They have no reference prefix.

Every assembly part has a Screenly part number, see the [Part Numbering Standard](part-numbering-standard.md).

## Classes

### `ADH`: Adhesives

Adhesives and adhesive tapes used in assembly, such as glue for enclosure parts, threadlockers and double-sided mounting tape.

### `ADP`: Power Adapters

External power adapters, wall plug or desktop, that ship with the product. Adapters are certified per region and listed in the product's safety and regulatory documents.

### `DOC`: Printed Documents

Printed documents that ship with the product, such as quick start guides, user manuals, and safety, regulatory and warranty information.

### `ENC`: Enclosure Parts and Assemblies

Mechanical parts of the product enclosure, made to Screenly drawings: housings, covers, brackets, light pipes, button caps, windows and gaskets, and pre-assembled groups of them.

### `ESP`: Electronic Semi Products

Electronic assemblies built separately and used as a part of the product, such as a Screenly daughterboard PCBA.

### `LBL`: Stickers and Labels

Labels and stickers made to Screenly drawings: product and rating labels, serial number labels, and regulatory, warning and packaging labels.

### `PAC`: Product Packages

Product packaging made to Screenly drawings: retail boxes, shipping cartons, inserts, trays, bags and foam.

### `PCB`: Printed Circuit Boards

Bare printed circuit boards made from a Screenly KiCad design. Each part is one revision of one design.

### `PSP`: Programmed Semi Products

Parts that are programmed with Screenly firmware or data before assembly, such as a pre-programmed microcontroller or a memory card with an operating system image. Each part is one unprogrammed part combined with one firmware or image version, which links it to its SBOM.

### `SCR`: Screws

Screws for assembling boards and enclosure parts.

## Open Items

- How assembly parts are added to the manufacturing BOM and HBOM of a build.
