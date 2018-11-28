/*********************************************************************
*                SEGGER MICROCONTROLLER GmbH & Co. KG                *
*        Solutions for real time microcontroller applications        *
**********************************************************************
*                                                                    *
*           (C) 2009    SEGGER Microcontroller GmbH & Co. KG         *
*                                                                    *
*        Internet: www.segger.com    Support:  support@segger.com    *
*                                                                    *
**********************************************************************
----------------------------------------------------------------------
File    : RAMCodeV2_Marvell_88MW300_ExtQSPI0_W25Qxx_NOR.c
Purpose : Implementation of RAMCode for custom hardware based on:
          W25Qxx NOR flash
---------------------------END-OF-HEADER------------------------------
*/

#include "RAMCodeV2.h"

#define U8  unsigned char
#define U16 unsigned short
#define U32 unsigned long

#define I8  signed char
#define I16 signed short
#define I32 signed long

/* Register values for MW300 */
#define GPIO            ((PINMUX_REGS*)0x46060000)
#define QSPI           ((QSPI_REGS*)0x46010000)
#define WDT             ((WDT_REGS*)0x48040000)


#define SECTOR_SIZE_SHIFT (12) // 4 KB sectors
#define PAGE_SIZE_SHIFT   (8)  // 256 byte pages

//
// Flash commands
//
#define CMD_WRITE_EN              0x06 // Write Enable
#define CMD_WRITE_DI              0x04 // Write Disable
#define CMD_READ_STATUS_1         0x05 // Read Status Register-1
#define CMD_READ_STATUS_2         0x35 // Read Status Register-2
#define CMD_WRITE_STATUS          0x01 // Write Status Register
#define CMD_READ_ID               0x90 // Read flash ID
#define CMD_READ                  0x03 // Read flash

#define CMD_PROGRAM_PAGE          0x02 // Page Program
#define CMD_PROGRAM_QUAD_PAGE     0x32 // Quad Page Program
#define CMD_ERASE_SECTOR          0x20 // Sector Erase ( 4 KB)
#define CMD_ERASE_BLOCK           0x52 // Block Erase  (32 KB)
#define CMD_ERASE_BLOCK2          0xD8 // Block Erase  (64 KB)
#define CMD_ERASE_CHIP            0xC7 // Chip Erase
#define CMD_SUSPEND               0x75 // Erase / Program Suspend
#define CMD_RESUME                0x7A // Erase / Program Resume
#define CMD_POWER_DOWN            0xB9 // Power-down

//
// Define flash sizes
//
#define WINBOND_2MB_FLASH         0x14
#define WINBOND_4MB_FLASH         0x15
#define WINBOND_8MB_FLASH         0x16
#define WINBOND_16MB_FLASH        0x17

/*********************************************************************
*
*       Types
*
**********************************************************************
*/

typedef struct {
  volatile U32 CR;
  volatile U32 TORR;
  volatile U32 CCVR;
  volatile U32 CRR;
  volatile U32 STAT;
  volatile U32 EOI;
} WDT_REGS;

typedef struct {
  volatile U32 CNTL;
  volatile U32 CONF;
  volatile U32 DOUT;
  volatile U32 DIN;
  volatile U32 INSTR;  // 0x10
  volatile U32 ADDR;
  volatile U32 RDMODE;
  volatile U32 HDRCNT;
  volatile U32 DINCNT; // 0x20
  volatile U32 TIMING;
  volatile U32 CONF2;
  volatile U32 ISR;
  volatile U32 IMR;    // 0x30
  volatile U32 IRSR;
  volatile U32 ISC;
} QSPI_REGS;

typedef struct {
  volatile U32 GPIO_PINMUX[80];
} PINMUX_REGS;

/*********************************************************************
*
*       Static code
*
**********************************************************************
*/

/*********************************************************************
*
*       _ReadID
*
*  Function description
*    Reads flash device ID
*/
U16 _ReadID(void) {
  U32 NumBytesRem;
  U16 Id;

  NumBytesRem = 2;
  Id = 0;
  //
  // FLUSH_FIFO
  //
  QSPI->CONF |= 1 << 9;
  while((QSPI->CONF & (1 << 9)));
  //
  // Prepare register for erase
  //
  QSPI->HDRCNT = 0
               | (0x1 <<  0)                // Set instr byte count
               | (0x3 <<  4)                // Set addr byte count
               | (0x0 <<  8)                // Set read mode count
               | (0x0 << 12)                // Set Dummy byte count
               ;
  QSPI->RDMODE &= ~(0xFFFF);               // Set read mode
  QSPI->DINCNT = NumBytesRem;                 // Number of items to read?
  QSPI->ADDR = 0;                 // Set addr
  QSPI->CONF &= (~(1 << 12) | ~(1 << 11)); // Set single address/data pin mode
  QSPI->INSTR = CMD_READ_ID;                      // Set read instruction
  QSPI->CONF &= ~(1 << 5);                 // Set one byte length mode
  //
  // Start transfer
  //
  QSPI->CNTL   |= (1 << 0);                 // Enable chip selected
  while((QSPI->CNTL & (1 << 1)) == 0);      // Wait until interface is ready (chip select status changed)
  QSPI->CONF   &=  ~(1 << 13);              // Set r/w mode to read
  QSPI->CONF   |=  (1 << 15);               // Start transfer
  while ((QSPI->CNTL & (1 << 1)) == 0);     // Wait while SPI controller is busy
  do {
    while ((QSPI->CNTL & (1 << 1)) == 0);   // Wait while SPI controller is busy
    while(QSPI->CNTL & (1 << 4));           // Waiting for RFIFO not empty
    Id <<= 8;
    Id |= QSPI->DIN & 0xFF;
  } while (--NumBytesRem);
  QSPI->CNTL   &= ~(1 << 0);                // Disable chip selected
  while((QSPI->CNTL & (1 << 1)) == 0);      // Wait until interface is ready (chip select status changed)
  return Id;
}

/*********************************************************************
*
*       _WaitWhileFlashBusy
*
*  Function description
*    Waits for the current operation to finish.
*    Also checks if an error occurred during the operation.
*
*  Return value
*      0  O.K.
*    < 0  Error
*/
static void _WaitWhileFlashBusy(void) {
  U32 Status;
  //
  // Prepare register for WE
  //
  QSPI->HDRCNT = 0
               | (0x1 <<  0)               // Set instr byte count
               | (0x0 <<  4)               // Set addr byte count
               | (0x0 <<  8)               // Set read mode count
               | (0x0 << 12)               // Set Dummy byte count
               ;
  QSPI->DINCNT = 0;                       // Set data in counter to 0 (means that data is continously shifted in until QSPI is stopped manually)
  QSPI->CONF  &= ~(3 << 10);              // Select 1 data pin mode
  QSPI->INSTR  = CMD_READ_STATUS_1;       // write instruction to be performed in the instruction register
  QSPI->CONF  &= ~(1 << 5);               // Select byte length 1
  //
  // Start transfer
  //
  QSPI->CNTL   |= (1 << 0);               // Enable serial select
  while((QSPI->CNTL & (1 << 1)) == 0);    // Wait until interface is ready
  QSPI->CONF   &= ~(1 << 13);             // set read data
  QSPI->CONF   |=  (1 << 15);             // Start transfer
  do {
    FLASH_FeedWatchdog(0);
    //
    // Get status register byte
    //
    while(QSPI->CNTL & (1 << 4));         // Wait if Rx FIFO is empty
    Status = (QSPI->DIN & 0xFF);
    if ((Status & 1) == 0) {
      break;
    }
  } while (1);
  //
  // Stop QSPI
  //
  while((QSPI->CNTL & (1 << 1)) == 0);    // Wait until interface is ready
  QSPI->CONF |= 1 << 14;                  // Stop QSPI
  while(QSPI->CONF & (1 << 15));          // Wait until QSPI release start signal
  QSPI->CNTL   &= ~(1 << 0);              // Disable chip select
  while((QSPI->CNTL & (1 << 1)) == 0);    // Wait until interface is ready
  //
  // Flush FIFOs to make sure there are no bytes left that we did not read so far
  //
  QSPI->CONF   |=  (1 <<  9);
  while(QSPI->CONF & (1 << 9));
}

/*********************************************************************
*
*       _SetWriteEnable()
*
*/
static U32 _SetWriteEnable(U32 Cmd) {
  //
  // Prepare register for WE
  //
  QSPI->HDRCNT = 0
               | (0x1 <<  0)              // Set instr byte count
               | (0x0 <<  4)              // Set addr byte count
               | (0x0 <<  8)              // Set read mode count
               | (0x0 << 12)              // Set Dummy byte count
               ;
  QSPI->DINCNT = 0;                       // Data in count
  QSPI->INSTR  = Cmd;
  QSPI->CNTL   |= (1 << 0);               // Enable serial select
  while((QSPI->CNTL & (1 << 1)) == 0);    // Wait until interface is ready
  QSPI->CONF   |=  (1 << 13) | (1 << 15); // Set direction to write and start transfer
  //
  // Stop QSPI transfer
  //
  while((QSPI->CNTL & (1 << 1)) == 0);    // Wait until interface is ready
  while((QSPI->CNTL & (1 << 6)) == 0);    // Wait until WFIFO is empty
  QSPI->CONF |= 1 << 14;                  // Stop QSPI
  while(QSPI->CONF & (1 << 15));          // Wait until QSPI release start signal
  QSPI->CNTL   &= ~(1 << 0);              // Disable chip select
  while((QSPI->CNTL & (1 << 1)) == 0);    // Wait until interface is ready
  return 0;
}


/*********************************************************************
*
*       FLASH_GetDesc
*
*  Function description
*    Get flash parameters such as min. alignment of the algorithm (for NAND flash usually 1 page),
*    flash size, block size, ...
*
*  Parameters
*    pContext Pointer to context area which can be used to store additional data.
*             The values of this area are maintained until the RAMCode is downloaded again.
*             This area can be freely used by the RAMCode to store additional parameters.
*             This area is 64 bytes in size.
*
*/
void FLASH_GetDesc(void* pContext, RAMCODE_RESULT_INFO* pResult, const RAMCODE_CMD_INFO* pInfo) {
  RAMCODE_DESC* pDesc = (RAMCODE_DESC*)pInfo->pBuffer;
  U16 Id;

  pDesc->AlgoDesc.NumExtraBytes           = 0;
  pDesc->AlgoDesc.MinAlign                = 8;                  // Min align is 2KB which is (2^11)
  pDesc->AlgoDesc.AutoErase               = 0;
  pDesc->AlgoDesc.SupportRead             = 1;
  pDesc->AlgoDesc.SupportEraseSector      = 1;
  pDesc->AlgoDesc.SupportEraseChip        = 1;
  pDesc->AlgoDesc.SupportMultiSectorErase = 1;
  pDesc->AlgoDesc.SupportMultiSectorProg  = 1;
  pDesc->AlgoDesc.AlgoRequiresClockSpeed  = 0;
  pDesc->AlgoDesc.HaltIfPCLeavesRAMCode   = 1;
  pDesc->FlashDesc.NumBlocks              = 1;
  pDesc->FlashDesc.BlockInfo.Offset       = 0;
  pDesc->FlashDesc.BlockInfo.NumSectors   = 4096;
  pDesc->FlashDesc.BlockInfo.SectorSize   = 1uL << SECTOR_SIZE_SHIFT;  // 256 Bytes
  //
  // Determine flash size
  //
  Id = _ReadID();
  switch (Id & 0xFF) {
  case WINBOND_2MB_FLASH:  pDesc->FlashDesc.BlockInfo.NumSectors =  512; break;
  case WINBOND_4MB_FLASH:  pDesc->FlashDesc.BlockInfo.NumSectors = 1024; break;
  case WINBOND_8MB_FLASH:  pDesc->FlashDesc.BlockInfo.NumSectors = 2048; break;
  case WINBOND_16MB_FLASH: pDesc->FlashDesc.BlockInfo.NumSectors = 4096; break;
  default:
    pDesc->FlashDesc.BlockInfo.NumSectors = 4096;
  }
}

/*********************************************************************
*
*       Read
*
*  Function description
*    This function reads the flash memory at a given offset.
*
*  Parameters
*    pInfo->Cmd                    Current command
*    pInfo->pBuffer                Pointer to buffer which is used to hold read/write data
*    pInfo->BufferSize             Size of the buffer which is used to hold read/write data
*    pInfo->BaseAddr               Base address where flash is located (0x0 for non-memory mapped flashes)
*    pInfo->Offset                 Offset into flash where programming/reading/erasing shall start
*    pInfo->NumBytes/NumSectors    NumBytes that shall be read/programmed or number of sectors that shall be erased
*    pInfo->Para0                  BaseAddr    Base address where flash is located (0x0 for non-memory mapped flashes)
*    pInfo->Para1                  SectorAddr  Address of current sector
*    pInfo->Para2                  SectorIndex Index of current sector
*
*    pResult->ErrorCode            See "Error codes" below
*    pResult->NumItemsRem          Describes how many bytes could not be erased
*    pResult->FailData             Not used in this function
*
*  Error codes
*    0 = Operation completed successfully
*    1 = Block verification error (Detected by generic RAMCode, do not use!)
*    2 = Item verification error
*    3 = Timeout occurred
*    4 = Program error
*    5 = Program 1 over 0
*    6 = Sector is locked
*    7 = Erase error
*    8 = No flash memory
*    9 = Generic error
*   >9 = Unspecified error (reserved for further error codes)
*   <0 = Algo depending error code (usually a small integer such as -1, -2, -3)
*/
void FLASH_Read(void* pContext, RAMCODE_RESULT_INFO* pResult, const RAMCODE_CMD_INFO* pInfo) {
  volatile U8 * pDest;
  U32 NumBytesRem;

  pDest       = (U8*)pInfo->pBuffer;
  NumBytesRem = pInfo->NumBytes;
  //
  // FLUSH_FIFO
  //
  QSPI->CONF |= 1 << 9;
  while((QSPI->CONF & (1 << 9)));
  //
  // Prepare register for erase
  //
  QSPI->HDRCNT = 0
               | (0x1 <<  0)                // Set instr byte count
               | (0x3 <<  4)                // Set addr byte count
               | (0x0 <<  8)                // Set read mode count
               | (0x0 << 12)                // Set Dummy byte count
               ;
  QSPI->RDMODE &= ~(0xFFFF);               // Set read mode
  QSPI->DINCNT = NumBytesRem;              // Number of items to read?
  QSPI->ADDR = pInfo->Offset;              // Set addr
  QSPI->CONF &= (~(1 << 12) | ~(1 << 11)); // Set single address/data pin mode
  QSPI->INSTR = CMD_READ;                  // Set read instruction
  QSPI->CONF &= ~(1 << 5);                 // Set one byte length mode
  //
  // Start transfer
  //
  QSPI->CNTL   |= (1 << 0);                 // Enable chip selected
  while((QSPI->CNTL & (1 << 1)) == 0);      // Wait until interface is ready (chip select status changed)
  QSPI->CONF   &=  ~(1 << 13);              // Set r/w mode to read
  QSPI->CONF   |=  (1 << 15);               // Start transfer
  while ((QSPI->CNTL & (1 << 1)) == 0);     // Wait while SPI controller is busy
  do {
    while ((QSPI->CNTL & (1 << 1)) == 0);   // Wait while SPI controller is busy
    while(QSPI->CNTL & (1 << 4));           // Waiting for RFIFO not empty
    *pDest++ = QSPI->DIN & 0xFF;
  } while (--NumBytesRem);
  QSPI->CNTL   &= ~(1 << 0);                // Disable chip selected
  while((QSPI->CNTL & (1 << 1)) == 0);      // Wait until interface is ready (chip select status changed)
}

/*********************************************************************
*
*       FLASH_Program
*
*  Purpose:
*    Programs the flash memory.
*
*  Parameters
*    pInfo->Cmd                    Current command
*    pInfo->pBuffer                Pointer to buffer which is used to hold read/write data
*    pInfo->BufferSize             Size of the buffer which is used to hold read/write data
*    pInfo->BaseAddr               Base address where flash is located (0x0 for non-memory mapped flashes)
*    pInfo->Offset                 Offset into flash where programming/reading/erasing shall start
*    pInfo->NumBytes/NumSectors    NumBytes that shall be read/programmed or number of sectors that shall be erased
*    pInfo->Para0                  BaseAddr    Base address where flash is located (0x0 for non-memory mapped flashes)
*    pInfo->Para1                  SectorAddr  Address of current sector
*    pInfo->Para2                  SectorIndex Index of current sector
*
*    pResult->ErrorCode            See "Error codes" below
*    pResult->FailAddr             Describes at which address programming failed
*    pResult->FailData             Not used in this function
*
*  Error codes
*    0 = Operation completed successfully
*    1 = Block verification error (Detected by generic RAMCode, do not use!)
*    2 = Item verification error
*    3 = Timeout occurred
*    4 = Program error
*    5 = Program 1 over 0
*    6 = Sector is locked
*    7 = Erase error
*    8 = No flash memory
*    9 = Generic error
*   >9 = Unspecified error (reserved for further error codes)
*   <0 = Algo depending error code (usually a small integer such as -1, -2, -3)
*/
void FLASH_Program(void* pContext, RAMCODE_RESULT_INFO* pResult, const RAMCODE_CMD_INFO* pInfo) {
  U32 NumBytesRem;
  U8* pSrc;
  U32 DestAddr;
  int i;

  pSrc               = (U8*)pInfo->pBuffer;
  DestAddr           = pInfo->Offset;
  NumBytesRem        = pInfo->NumBytes;
  pResult->ErrorCode = 0;
  //
  // Flush r/w FIFOs and wait until flush completed
  // Not necessary for each page since we always wait until all FIFOs are empty
  //
  QSPI->CONF   |=  (1 <<  9);
  while(QSPI->CONF & (1 << 9));
  //
  // Program page-wise
  //
  do {
    FLASH_FeedWatchdog(0);
    _SetWriteEnable(CMD_WRITE_EN);            // Set write-enable on flash. Auto-cleared by hardware after flash operation
    //
    // Prepare register for program
    //
    QSPI->HDRCNT = 0
                 | (0x1 <<  0)                 // Set instr byte count
                 | (0x3 <<  4)                 // Set addr byte count
                 | (0x0 <<  8)                 // Set read mode count
                 | (0x0 << 12)                 // Set Dummy byte count
                 ;
    QSPI->CONF  &= ~(1 << 12) | ~(3 << 10);   // Select 1 address pin mode and 1 data pin mode
    QSPI->ADDR   = (DestAddr & 0xFFFFFF);
    QSPI->INSTR  = CMD_PROGRAM_PAGE;          // write instruction to be performed in the instruction register
    QSPI->CONF  &= ~(1 << 5);                 // Select the number of bytes in each serial interface transfer to 1
    //
    // Start transfer
    //
    QSPI->CNTL   |= (1 << 0);                 // Enable serial select
    while((QSPI->CNTL & (1 << 1)) == 0);      // Wait until interface is ready
    QSPI->CONF   |=  (1 << 13) | (1 << 15);   // Set direction == write and start transfer
    //
    // Write complete page
    //
    i = 0;
    do {
      while(QSPI->CNTL & (1 << 7));           // Wait until there is some space in the WFIFO
      QSPI->DOUT = *pSrc++;
      while(QSPI->CNTL & (1 << 7));           // Wait until there is some space in the WFIFO
      QSPI->DOUT = *pSrc++;
      while(QSPI->CNTL & (1 << 7));           // Wait until there is some space in the WFIFO
      QSPI->DOUT = *pSrc++;
      while(QSPI->CNTL & (1 << 7));           // Wait until there is some space in the WFIFO
      QSPI->DOUT = *pSrc++;
      i += 4;
    } while (i < (1 << PAGE_SIZE_SHIFT));
    //
    // Stop QSPI transfer
    //
    while((QSPI->CNTL & (1 << 1)) == 0);      // Wait until interface is ready
    while((QSPI->CNTL & (1 << 6)) == 0);      // Wait until WFIFO is empty
    QSPI->CONF |= 1 << 14;                    // Stop QSPI
    while(QSPI->CONF & (1 << 15));            // Wait until QSPI release start signal
    QSPI->CNTL   &= ~(1 << 0);                // Disable chip select
    while((QSPI->CNTL & (1 << 1)) == 0);      // Wait until interface is ready
    //
    // Wait until flash is ready again
    //
    _WaitWhileFlashBusy();
    //
    // Adjust variable values
    //
    NumBytesRem -= (1 << PAGE_SIZE_SHIFT);
    DestAddr    += (1 << PAGE_SIZE_SHIFT);
  } while (NumBytesRem);
}

/*********************************************************************
*
*       FLASH_Erase
*
*  Function description
*    Erases one or more flash sectors. Caller is responsible for
*    setting pInfo->Offset to a value which is the start of a sector.
*
*  Parameters
*    pInfo->Cmd                    Current command
*    pInfo->pBuffer                Pointer to buffer which is used to hold read/write data
*    pInfo->BufferSize             Size of the buffer which is used to hold read/write data
*    pInfo->BaseAddr               Base address where flash is located (0x0 for non-memory mapped flashes)
*    pInfo->Offset                 Offset into flash where programming/reading/erasing shall start
*    pInfo->NumBytes/NumSectors    NumBytes that shall be read/programmed or number of sectors that shall be erased
*    pInfo->Para0                  BaseAddr    Base address where flash is located (0x0 for non-memory mapped flashes)
*    pInfo->Para1                  SectorAddr  Address of current sector
*    pInfo->Para2                  SectorIndex Index of current sector
*
*    pResult->ErrorCode            See "Error codes" below
*    pResult->NumItemsRem          Describes how many flash blocks could not be erased
*    pResult->FailData             Not used in this function
*
*  Error codes
*    0 = Operation completed successfully
*    1 = Block verification error (Detected by generic RAMCode, do not use!)
*    2 = Item verification error
*    3 = Timeout occurred
*    4 = Program error
*    5 = Program 1 over 0
*    6 = Sector is locked
*    7 = Erase error
*    8 = No flash memory
*    9 = Generic error
*   >9 = Unspecified error (reserved for further error codes)
*   <0 = Algo depending error code (usually a small integer such as -1, -2, -3)
*/
void FLASH_Erase(void* pContext, RAMCODE_RESULT_INFO* pResult, const RAMCODE_CMD_INFO* pInfo) {
  U32 NumSectorsRem;
  U32 SectorAddr;

  pResult->ErrorCode = 0;

  if (pInfo->NumSectors == 0) {

  //Erase entire chip
  //
  // Flush r/w FIFOs and wait until flush completed
  // Not necessary for each page since we always wait until all FIFOs are empty
  //
    QSPI->CONF   |=  (1 <<  9);
    while(QSPI->CONF & (1 << 9));

    FLASH_FeedWatchdog(0);

    _SetWriteEnable(CMD_WRITE_EN);


    QSPI->INSTR  = CMD_ERASE_CHIP;

    //
    // Start transfer
    //
    QSPI->CNTL   |= (1 << 0);                 // Enable chip selected
    while((QSPI->CNTL & (1 << 1)) == 0);      // Wait until interface is ready (chip select status changed)
    QSPI->CONF   |=  (1 << 13);               // Set r/w mode to write
    QSPI->CONF   |=  (1 << 15);               // Start transfer
    //
    // Stop transfer
    //
    while((QSPI->CNTL & (1 << 1)) == 0);      // Wait until interface is ready
    while((QSPI->CNTL & (1 << 6)) == 0);      // Wait until WFIFO is empty
    QSPI->CONF   |= 1 << 14;                  // Stop QSPI
    while(QSPI->CONF & (1 << 15));            // Wait until QSPI release start signal
    QSPI->CNTL   &= ~(1 << 0);                // serial select is deactivated (output is driven high)
    while((QSPI->CNTL & (1 << 1)) == 0);      // Wait until interface is ready
    //
    // Wait until flash has finished operation
    //

    _WaitWhileFlashBusy();
   return;
  }

  SectorAddr    = pInfo->Offset;
  NumSectorsRem = pInfo->NumSectors;
  //
  // We erase sector wise (4KB)
  //
  SectorAddr   &= 0x00FFFFFF;                   // Flash area max 16 MB. Flash does not use abolsute addresses, so we use a relative sector address
  //
  // Flush r/w FIFOs and wait until flush completed
  // Not necessary for each page since we always wait until all FIFOs are empty
  //
  QSPI->CONF   |=  (1 <<  9);
  while(QSPI->CONF & (1 << 9));
  do {
    FLASH_FeedWatchdog(0);
    _SetWriteEnable(CMD_WRITE_EN);            // Set write-enable on flash. Auto-cleared by hardware after flash operation
    //
    // Prepare register for erase
    //
    QSPI->HDRCNT = 0
                 | (0x1 <<  0)                // Set instr byte count
                 | (0x3 <<  4)                // Set addr byte count
                 | (0x0 <<  8)                // Set read mode count
                 | (0x0 << 12)                // Set Dummy byte count
                 ;
    QSPI->CONF  &= ~(1 << 12);                // Select 1 address pin mode
    QSPI->ADDR   = SectorAddr;                // Set sector addr
    QSPI->INSTR  = CMD_ERASE_SECTOR;          // Write erase instruction
    //
    // Start transfer
    //
    QSPI->CNTL   |= (1 << 0);                 // Enable chip selected
    while((QSPI->CNTL & (1 << 1)) == 0);      // Wait until interface is ready (chip select status changed)
    QSPI->CONF   |=  (1 << 13);               // Set r/w mode to write
    QSPI->CONF   |=  (1 << 15);               // Start transfer
    //
    // Stop transfer
    //
    while((QSPI->CNTL & (1 << 1)) == 0);      // Wait until interface is ready
    while((QSPI->CNTL & (1 << 6)) == 0);      // Wait until WFIFO is empty
    QSPI->CONF   |= 1 << 14;                  // Stop QSPI
    while(QSPI->CONF & (1 << 15));            // Wait until QSPI release start signal
    QSPI->CNTL   &= ~(1 << 0);                // serial select is deactivated (output is driven high)
    while((QSPI->CNTL & (1 << 1)) == 0);      // Wait until interface is ready
    SectorAddr += 1 << SECTOR_SIZE_SHIFT;
    //
    // Wait until flash has finished operation
    //
    _WaitWhileFlashBusy();
  } while (--NumSectorsRem);
}

/*********************************************************************
*
*       FLASH_Prepare
*
*  Function description
*    Performs some initialization which is necessary for the target
*    to be able to work with the NAND flash.
*/
void FLASH_Prepare(void* pContext) {


   // Add part to turn on VDDIO: PMU_PowerOnVDDIO(PMU_VDDIO_2);
   // GPIO pins GPIO_28/29/30/31/32/33 are used for QSPI communication
   *(volatile U32*)(0x480A00A4) |= (1 << 2);
   *(volatile U32*)(0x480A00A4) |= (1 << 14);

  *(volatile U32*)(0x480A007C) &= ~(1 << 1);   // Enable QSPI clock

  QSPI->CONF &= ~(0x1F);                       // Set CLK_PRESCALE to 0
  *(volatile U32*)(0x480A0094) &= ~(7 << 8);   //  Clear QSPI_CLK_DIV
  *(volatile U32*)(0x480A0094) |= (4 << 8);    //  QSPI_CLK_DIV = 4

  //
  // Configure pins
  //
  GPIO->GPIO_PINMUX[28] &= (~(1 << 15) | ~(7 << 0));        // Pull-Up
  GPIO->GPIO_PINMUX[28] |= 1 << 0;                          // Pinmux function 0
  GPIO->GPIO_PINMUX[29] &= (~(1 << 15) | ~(7 << 0));        // Pull-Up
  GPIO->GPIO_PINMUX[29] |= 1 << 0;                          // Pinmux function 0
  GPIO->GPIO_PINMUX[30] &= (~(1 << 15) | ~(7 << 0));        // Pull-Up
  GPIO->GPIO_PINMUX[30] |= 1 << 0;                          // Pinmux function 0
  GPIO->GPIO_PINMUX[31] &= (~(1 << 15) | ~(7 << 0));        // Pull-Up
  GPIO->GPIO_PINMUX[31] |= 1 << 0;                          // Pinmux function 0
  GPIO->GPIO_PINMUX[32] &= (~(1 << 15) | ~(7 << 0));        // Pull-Up
  GPIO->GPIO_PINMUX[32] |= 1 << 0;                          // Pinmux function 0
  GPIO->GPIO_PINMUX[33] &= (~(1 << 15) | ~(7 << 0));        // Pull-Up
  GPIO->GPIO_PINMUX[33] |= 1 << 0;                          // Pinmux function 0
  //
  // Diasble flash power down mode
  //
  QSPI->CONF |= 1 << 9;
  while((QSPI->CONF & (1 << 9)) == 1);
  //
  // Prepare register for power down
  //
  QSPI->HDRCNT = 0
               | (0x1 <<  0)                // Set instr byte count
               | (0x0 <<  4)                // Set addr byte count
               | (0x0 <<  8)                // Set read mode count
               | (0x0 << 12)                // Set Dummy byte count
               ;
  QSPI->DINCNT = 0;                // Data in counter
  QSPI->INSTR = 0xAB;              // Release power down
  //
  // Start transfer
  //
  QSPI->CNTL   |= (1 << 0);                 // Enable chip selected
  while((QSPI->CNTL & (1 << 1)) == 0);      // Wait until interface is ready (chip select status changed)
  QSPI->CONF   |=  (1 << 13);               // Set r/w mode to write
  QSPI->CONF   |=  (1 << 15);               // Start transfer
  //
  // Stop transfer
  //
  while(QSPI->CNTL & (1 << 1) == 0);
  while(QSPI->CNTL & (1 << 6) == 0);        // Wait until wfifo empty
  QSPI->CONF |= (1 << 14);                  // Stop QSPI
  while(QSPI->CONF & (1 << 15));            // Wait until QSPI release start signal
  QSPI->CNTL   &= ~(1 << 0);                // Disable chip selected
  while((QSPI->CNTL & (1 << 1)) == 0);      // Wait until interface is ready (chip select status changed)}
}

/*********************************************************************
*
*       FLASH_Restore
*
*  Function description
*    Restores all settings which have been changed by FLASH_Prepare and
*    which need a restore to guarantee proper target application execution.
*/
void FLASH_Restore(void* pContext) {
  (void)pContext;
}

/*********************************************************************
*
*       FLASH_FeedWatchdog
*
*  Function description
*    Called from inside this module as well as from the generic part
*/
void FLASH_FeedWatchdog(void* pContext) {
  (void)pContext;
  if (WDT->CR & 1) {  // Watchdog enabled? Feed it!
    WDT->CRR = 0x76;
  }
}

/**************************** End of file ***************************/
