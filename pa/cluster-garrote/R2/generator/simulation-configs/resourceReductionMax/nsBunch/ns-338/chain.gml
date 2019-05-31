graph [
  node [
    id 0
    label 1
    disk 8
    cpu 3
    memory 13
  ]
  node [
    id 1
    label 2
    disk 4
    cpu 4
    memory 4
  ]
  node [
    id 2
    label 3
    disk 5
    cpu 3
    memory 3
  ]
  node [
    id 3
    label 4
    disk 3
    cpu 4
    memory 2
  ]
  node [
    id 4
    label 5
    disk 9
    cpu 4
    memory 11
  ]
  node [
    id 5
    label 6
    disk 4
    cpu 3
    memory 3
  ]
  node [
    id 6
    label "start"
  ]
  edge [
    source 0
    target 6
    delay 31
    bw 140
  ]
  edge [
    source 0
    target 1
    delay 31
    bw 128
  ]
  edge [
    source 1
    target 2
    delay 34
    bw 91
  ]
  edge [
    source 1
    target 3
    delay 30
    bw 53
  ]
  edge [
    source 1
    target 4
    delay 29
    bw 68
  ]
  edge [
    source 2
    target 5
    delay 25
    bw 101
  ]
  edge [
    source 3
    target 5
    delay 32
    bw 182
  ]
  edge [
    source 4
    target 5
    delay 26
    bw 104
  ]
]