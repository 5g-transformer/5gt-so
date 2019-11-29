# common R2 test
`r2_common_test.py` includes 2 testing scenarios that check if the algorithms
are R2 compliant. It is a python unit test script that works against running
server stubs of the PAs. Both scenarios use the VCDN nsd.

# Test scenario resources
The testing infrastructure has x2 NFVI PoPs, one with coordinates of UC3M, and
another with coordinates of CTTC.
Both NFVI PoPs have enough resources to host all VNFs, and only UC3M NFVI PoP
has MEC capabilities. A LL interconnects the NFVI PoPs.

## *test_PA_mec_location* scenario
This scenario imposes:
 * MEC constraint to the webserver
 * video SAP to be located at UC3M
 * mgt SAP to be located at CTTC
 * a low delay for the VideoDistribution link, so spr21 is co-located with the
   webserver
 * a low delay for the mgt VL, such that spr1 VNF is co-located with mgt SAP

The output must satisfy:
 * webserver, spr21 and video SAP are placed at UC3M
 * videoData VL is deployed over the LL connecting NFVI PoPs
 * mgt SAP and spr1 are placed at CTTC

## *test_PA_dettached_video_sap* scenario
This scenario imposes:
 * location constraint for mgt SAP to be at CTTC
 * location constraint for the video SAP to be at UC3M
 * low delays for VideoDistribution and VideoData VLs, so webserver, spr21, and
   spr 1 are co-located with the video SAP

The output must satisfy:
 * every VNF is deployed at UC3M
 * mgt SAP is deployed at CTTC
 * video SAP is deployed at UC3M
 * mgt VL is deployed over the LL connecting NFVI PoPs

## Execution of the VCDN tests
There are 2 test scenarios, each of them with one variant per PA:
 * test_polito_uc3m_mec_location
 * test_polito_uc3m_dettached_video_sap
 * test_sssa_mec_location
 * test_sssa_dettached_video_sap
 * test_eurecom_mec_location
 * test_eurecom_dettached_video_sap

If you are executing *polito_uc3m* PA, you will execute:
```bash
python3 -m unittest r2_common_test.TestVCDN.test_polito_uc3m_mec_location r2_common_test.TestVCDN.test_polito_uc3m_dettached_video_sap -vvv
```
under the same directory where the script is created.

## Server stub parameters
In the beginning of `r2_common_test.py` you can find the variables that specify
the ip, port and URI that the test uses to invoke the server stubs.
Change them appropriately to your convenience.
