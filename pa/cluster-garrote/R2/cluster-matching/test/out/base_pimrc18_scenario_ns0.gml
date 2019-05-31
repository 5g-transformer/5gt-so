graph [
  node [
    id 0
    label "v_gen_1_6_1526292057.02"
    processing_time 9
    vnf_name "v_gen_1_6_1526292057.02"
    place_at []
    requirements [ 
      storage 6
      cpu 5
      memory 8
    ]
  ]
  node [
    id 1
    label "v_gen_6_19_1526292057.03"
    processing_time 3
    vnf_name "v_gen_6_19_1526292057.03"
    place_at []
    requirements [ 
      storage 2
      cpu 4
      memory 8
    ]
  ]
  node [
    id 2
    label "v_gen_2_3_1526292057.02"
    processing_time 5
    vnf_name "v_gen_2_3_1526292057.02"
    place_at []
    requirements [ 
      storage 4
      cpu 7
      memory 4
    ]
  ]
  node [
    id 3
    label "v_gen_8_15_1526292057.03"
    processing_time 3
    vnf_name "v_gen_8_15_1526292057.03"
    place_at []
    requirements [ 
      storage 8
      cpu 3
      memory 5
    ]
  ]
  node [
    id 4
    label "v_gen_5_15_1526292057.03"
    processing_time 10
    vnf_name "v_gen_5_15_1526292057.03"
    place_at []
    requirements [ 
      storage 4
      cpu 9
      memory 9
    ]
  ]
  node [
    id 5
    label "v_gen_7_9_1526292057.03"
    processing_time 7
    vnf_name "v_gen_7_9_1526292057.03"
    place_at []
    requirements [ 
      storage 5
      cpu 2
      memory 5
    ]
  ]
  node [
    id 6
    label "v_gen_4_9_1526292057.02"
    processing_time 10
    vnf_name "v_gen_4_9_1526292057.02"
    place_at []
    requirements [ 
      storage 3
      cpu 10
      memory 3
    ]
  ]
  node [
    id 7
    label "v_gen_3_2_1526292057.02"
    processing_time 2
    vnf_name "v_gen_3_2_1526292057.02"
    place_at []
    requirements [ 
      storage 10
      cpu 10
      memory 3
    ]
  ]
  edge [
    source 0
    target 2
    delay 2
    traffic 28
    prob 1.0
  ]
  edge [
    source 1
    target 5
    delay 14
    traffic 16
    prob 1.0
  ]
  edge [
    source 1
    target 6
    delay 2
    traffic 18
    prob 1.0
  ]
  edge [
    source 2
    target 6
    delay 7
    traffic 13
    prob 0.554080186081
  ]
  edge [
    source 2
    target 7
    delay 6
    traffic 26
    prob 0.445919813919
  ]
  edge [
    source 3
    target 5
    delay 7
    traffic 14
    prob 1.0
  ]
  edge [
    source 4
    target 5
    delay 12
    traffic 26
    prob 1.0
  ]
  edge [
    source 4
    target 7
    delay 11
    traffic 21
    prob 1.0
  ]
]
