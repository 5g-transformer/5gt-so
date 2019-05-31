graph [
  node [
    id 0
    label "v_gen_8_20_1526292057.01"
    processing_time 4
    vnf_name "v_gen_8_20_1526292057.01"
    place_at []
    requirements [ 
      storage 7
      cpu 10
      memory 8
    ]
  ]
  node [
    id 1
    label "v_gen_1_10_1526292057.0"
    processing_time 2
    vnf_name "v_gen_1_10_1526292057.0"
    place_at []
    requirements [ 
      storage 9
      cpu 4
      memory 3
    ]
  ]
  node [
    id 2
    label "v_gen_7_14_1526292057.01"
    processing_time 7
    vnf_name "v_gen_7_14_1526292057.01"
    place_at []
    requirements [ 
      storage 5
      cpu 5
      memory 9
    ]
  ]
  node [
    id 3
    label "v_gen_3_8_1526292057.0"
    processing_time 4
    vnf_name "v_gen_3_8_1526292057.0"
    place_at []
    requirements [ 
      storage 7
      cpu 7
      memory 9
    ]
  ]
  node [
    id 4
    label "v_gen_5_14_1526292057.01"
    processing_time 2
    vnf_name "v_gen_5_14_1526292057.01"
    place_at []
    requirements [ 
      storage 9
      cpu 4
      memory 8
    ]
  ]
  node [
    id 5
    label "v_gen_2_18_1526292057.0"
    processing_time 10
    vnf_name "v_gen_2_18_1526292057.0"
    place_at []
    requirements [ 
      storage 8
      cpu 5
      memory 8
    ]
  ]
  node [
    id 6
    label "v_gen_6_7_1526292057.01"
    processing_time 4
    vnf_name "v_gen_6_7_1526292057.01"
    place_at []
    requirements [ 
      storage 3
      cpu 2
      memory 3
    ]
  ]
  node [
    id 7
    label "v_gen_4_14_1526292057.0"
    processing_time 5
    vnf_name "v_gen_4_14_1526292057.0"
    place_at []
    requirements [ 
      storage 9
      cpu 6
      memory 6
    ]
  ]
  edge [
    source 0
    target 4
    delay 3
    traffic 29
    prob 0.706640017992
  ]
  edge [
    source 1
    target 5
    delay 13
    traffic 25
    prob 1.0
  ]
  edge [
    source 2
    target 4
    delay 11
    traffic 14
    prob 0.293359982008
  ]
  edge [
    source 3
    target 4
    delay 6
    traffic 19
    prob 0.146424715766
  ]
  edge [
    source 3
    target 5
    delay 12
    traffic 15
    prob 1.0
  ]
  edge [
    source 3
    target 6
    delay 12
    traffic 16
    prob 0.635702863603
  ]
  edge [
    source 3
    target 7
    delay 5
    traffic 12
    prob 0.217872420631
  ]
]
