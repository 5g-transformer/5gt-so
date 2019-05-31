graph [
  node [
    id 0
    label "v_gen_3_5_1526292057.01"
    processing_time 5
    vnf_name "v_gen_3_5_1526292057.01"
    place_at []
    requirements [ 
      storage 5
      cpu 2
      memory 8
    ]
  ]
  node [
    id 1
    label "v_gen_6_9_1526292057.02"
    processing_time 10
    vnf_name "v_gen_6_9_1526292057.02"
    place_at []
    requirements [ 
      storage 7
      cpu 10
      memory 10
    ]
  ]
  node [
    id 2
    label "v_gen_4_10_1526292057.01"
    processing_time 9
    vnf_name "v_gen_4_10_1526292057.01"
    place_at []
    requirements [ 
      storage 7
      cpu 4
      memory 8
    ]
  ]
  node [
    id 3
    label "v_gen_5_18_1526292057.02"
    processing_time 10
    vnf_name "v_gen_5_18_1526292057.02"
    place_at []
    requirements [ 
      storage 3
      cpu 7
      memory 10
    ]
  ]
  node [
    id 4
    label "v_gen_1_4_1526292057.01"
    processing_time 8
    vnf_name "v_gen_1_4_1526292057.01"
    place_at []
    requirements [ 
      storage 9
      cpu 6
      memory 2
    ]
  ]
  node [
    id 5
    label "v_gen_2_12_1526292057.01"
    processing_time 8
    vnf_name "v_gen_2_12_1526292057.01"
    place_at []
    requirements [ 
      storage 2
      cpu 2
      memory 4
    ]
  ]
  node [
    id 6
    label "v_gen_7_2_1526292057.02"
    processing_time 2
    vnf_name "v_gen_7_2_1526292057.02"
    place_at []
    requirements [ 
      storage 3
      cpu 7
      memory 2
    ]
  ]
  node [
    id 7
    label "v_gen_8_18_1526292057.02"
    processing_time 8
    vnf_name "v_gen_8_18_1526292057.02"
    place_at []
    requirements [ 
      storage 8
      cpu 4
      memory 3
    ]
  ]
  edge [
    source 0
    target 6
    delay 5
    traffic 29
    prob 1.0
  ]
  edge [
    source 0
    target 4
    delay 8
    traffic 30
    prob 0.719082383004
  ]
  edge [
    source 1
    target 6
    delay 14
    traffic 17
    prob 1.0
  ]
  edge [
    source 1
    target 3
    delay 14
    traffic 16
    prob 1.0
  ]
  edge [
    source 2
    target 3
    delay 2
    traffic 25
    prob 1.0
  ]
  edge [
    source 2
    target 5
    delay 5
    traffic 23
    prob 1.0
  ]
  edge [
    source 4
    target 5
    delay 2
    traffic 18
    prob 0.280917616996
  ]
  edge [
    source 6
    target 7
    delay 8
    traffic 24
    prob 1.0
  ]
]
