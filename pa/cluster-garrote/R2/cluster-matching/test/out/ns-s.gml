graph [
  node [
    id 0
    label "vnf2"
    vnf_name "vnf2"
    processing_time 2
    place_at [u'h1']
    requirements [ 
      storage 0.5
      cpu 1
      memory 2
    ]
    cluster 1
  ]
  node [
    id 1
    label "vnf3"
    vnf_name "vnf3"
    processing_time 0.5
    place_at [u'h2']
    requirements [ 
      storage 1
      cpu 1
      memory 1
    ]
    cluster 2
  ]
  node [
    id 2
    label "vnf1"
    vnf_name "vnf1"
    processing_time 4
    place_at [u'h1']
    requirements [ 
      storage 10
      cpu 1
      memory 4
    ]
    cluster 1
  ]
  node [
    id 3
    label "vnf4"
    vnf_name "vnf4"
    processing_time 10
    place_at [u'h2']
    requirements [ 
      storage 10
      cpu 4
      memory 8
    ]
    cluster 2
  ]
  node [
    id 4
    label "vnf5"
    vnf_name "vnf5"
    processing_time 0.1
    place_at [u'h2']
    requirements [ 
      storage 0.1
      cpu 1
      memory 0.5
    ]
    cluster 2
  ]
  edge [
    source 0
    target 1
    traffic 6
    prob 0.6
  ]
  edge [
    source 0
    target 2
    traffic 10
    prob 1.0
  ]
  edge [
    source 0
    target 3
    traffic 4
    prob 0.4
  ]
  edge [
    source 1
    target 4
    traffic 6
    prob 1.0
  ]
  edge [
    source 3
    target 4
    traffic 4
    prob 1.0
  ]
]
